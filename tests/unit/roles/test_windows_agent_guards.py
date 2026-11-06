"""Exercise Windows lifecycle decisions without installing or removing an agent."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def run_play(tmp_path, tasks, variables, check=False):
    executable = shutil.which("ansible-playbook")
    if not executable:
        pytest.skip("ansible-playbook is required")
    play = [
        {"hosts": "localhost", "gather_facts": False, "become": False, "tasks": tasks}
    ]
    path = tmp_path / "play.json"
    path.write_text(json.dumps(play))
    env = {k: v for k, v in os.environ.items() if not k.startswith("PATCHMON_")}
    env.update(
        {
            "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg"),
            "ANSIBLE_COLLECTIONS_PATH": str(ROOT / ".collections"),
            "ANSIBLE_INVENTORY_ENABLED": "host_list",
            "ANSIBLE_NOCOLOR": "1",
        }
    )
    command = [
        executable,
        "-i",
        "localhost,",
        "-c",
        "local",
        str(path),
        "-e",
        json.dumps(variables),
    ]
    if check:
        command.append("--check")
    return subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30
    )


@pytest.mark.parametrize(
    "service_info,force,new_host,expected",
    [
        ({"exists": True, "services": [{"state": "started"}]}, False, False, True),
        ({"exists": True, "services": [{"state": "started"}]}, True, False, False),
        ({"exists": True, "services": [{"state": "started"}]}, False, True, False),
        ({"exists": True, "services": [{"state": "stopped"}]}, False, False, False),
        (
            {"exists": True, "services": [{"state": "start_pending"}]},
            False,
            False,
            False,
        ),
        ({"exists": False, "services": []}, False, False, False),
        ({}, False, False, False),
    ],
)
def test_install_skip_decision(tmp_path, service_info, force, new_host, expected):
    # Execute the production Ansible decision with win_service_info fixtures.
    tasks = yaml.safe_load((ROOT / "roles/agent/tasks/windows/install.yml").read_text())
    decision = next(
        t
        for t in tasks
        if "__agent_win_already_running" in t.get("ansible.builtin.set_fact", {})
    )
    result = run_play(
        tmp_path,
        [
            decision,
            {
                "ansible.builtin.assert": {
                    "that": ["__agent_win_already_running == expected_skip"]
                }
            },
        ],
        {
            "__agent_win_service_info": service_info,
            "agent_force_install": force,
            "agent_force_new_host": new_host,
            "expected_skip": expected,
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("existing_script", [False, True])
@pytest.mark.parametrize("server_url", ["", "http://127.0.0.1:1"])
def test_windows_removal_check_mode(tmp_path, existing_script, server_url):
    controller = tmp_path / "remove.ps1"
    staged = tmp_path / "staged.ps1"
    if existing_script:
        controller.write_text("throw 'Removal script must not run in check mode'\n")
    original = controller.read_bytes() if existing_script else None
    result = run_play(
        tmp_path,
        [{"ansible.builtin.include_role": {"name": "patchmon.core.agent"}}],
        {
            "ansible_facts": {"os_family": "Windows"},
            "agent_state": "absent",
            "agent_server_url": server_url,
            "agent_verify_ssl": True,
            "agent_remove_script_controller_path": str(controller),
            "agent_remove_script_path": str(staged),
        },
        check=True,
    )
    output = result.stdout + result.stderr
    assert (result.returncode == 0) is bool(server_url), output
    if server_url:
        assert "Removal script changes cannot be predicted" in output
        assert (
            "TASK [patchmon.core.agent : Fetch the Windows agent removal script"
            not in output
        )
        assert (
            "TASK [patchmon.core.agent : Stage the Windows removal script" not in output
        )
        assert (
            "TASK [patchmon.core.agent : Run the PatchMon Windows agent removal script"
            not in output
        )
        assert "changed=0" in output
    else:
        assert "agent_server_url is required" in output
    assert not staged.exists()
    assert controller.exists() is existing_script
    if existing_script:
        assert controller.read_bytes() == original


@pytest.mark.parametrize(
    "platform,api_id,api_key,enrollment,success",
    [
        ("Windows", "host-id", "host-secret", False, True),
        ("Windows", "", "", True, True),
        ("Windows", "host-id", "host-secret", True, True),
        ("Windows", "host-id", "", True, False),
        ("Windows", "", "host-secret", True, False),
        ("Windows", "", "", False, False),
        ("Debian", "host-id", "host-secret", False, False),
        ("Debian", "", "", True, True),
    ],
)
def test_install_credentials(tmp_path, platform, api_id, api_key, enrollment, success):
    result = run_play(
        tmp_path,
        [{"ansible.builtin.include_role": {"name": "patchmon.core.agent"}}],
        {
            "ansible_facts": {"os_family": platform},
            "agent_state": "present",
            "agent_server_url": "http://127.0.0.1:1",
            "agent_api_id": api_id,
            "agent_api_key": api_key,
            "agent_enrollment_key": "enrollment-id" if enrollment else "",
            "agent_enrollment_secret": "enrollment-secret" if enrollment else "",
        },
        check=True,
    )
    output = result.stdout + result.stderr
    assert (result.returncode == 0) is success, output
    assert "host-secret" not in output
    assert "enrollment-secret" not in output
    if success:
        assert "changed=0" in output

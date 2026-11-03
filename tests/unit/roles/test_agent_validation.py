"""Exercise role validation through Ansible without contacting a managed host."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "facts,state,expected,need_enrollment,need_server",
    [
        ({"os_family": "Windows"}, "started", True, False, False),
        ({"os_family": "Windows"}, "stopped", True, False, False),
        ({"os_family": "Windows"}, "report", True, False, False),
        ({"os_family": "Windows"}, "present", True, True, False),
        ({"os_family": "Windows"}, "present", False, False, False),
        ({"os_family": "Windows"}, "absent", True, False, True),
        ({"os_family": "Windows"}, "absent", False, False, False),
        ({}, "started", True, False, False),
        ({"os_family": "Debian"}, "started", True, False, False),
        ({"os_family": "Debian"}, "present", True, True, False),
    ],
)
def test_agent_validation(
    tmp_path, facts, state, expected, need_enrollment, need_server
):
    executable = shutil.which("ansible-playbook")
    if not executable:
        pytest.skip("ansible-playbook is required")

    vars_data = {
        "ansible_facts": facts,
        "agent_state": state,
        # Avoid endpoint lookup requiring PATCHMON_SERVER_URL during unit tests.
        "agent_server_url": "",
        "agent_enrollment_key": "",
        "agent_enrollment_secret": "",
    }
    if need_enrollment:
        vars_data.update(
            {
                "agent_server_url": "https://patchmon.example.com",
                "agent_enrollment_key": "ek",
                "agent_enrollment_secret": "es",
            }
        )
    elif need_server:
        vars_data["agent_server_url"] = "https://patchmon.example.com"

    vars_files = [
        str(ROOT / "roles/agent/vars/main.yml"),
        str(ROOT / "roles/agent/defaults/main.yml"),
    ]
    if facts.get("os_family") == "Windows":
        # Unit tests include validate.yml outside role context, so role_path is
        # unset and the role's include_vars is skipped. Load Windows overrides here.
        vars_files.append(str(ROOT / "roles/agent/vars/Windows.yml"))

    play = [
        {
            "hosts": "localhost",
            "gather_facts": False,
            "vars_files": vars_files,
            "vars": vars_data,
            "tasks": [
                {
                    "ansible.builtin.include_tasks": str(
                        ROOT / "roles/agent/tasks/validate.yml"
                    )
                }
            ],
        }
    ]
    if facts.get("os_family") == "Windows" and expected:
        play[0]["vars"].update(
            {
                "expected_binary": r"C:\Program Files\PatchMon\patchmon-agent.exe",
                "expected_config": r"C:\ProgramData\PatchMon",
            }
        )
        play[0]["tasks"].append(
            {
                "ansible.builtin.assert": {
                    "that": [
                        "agent_service_name == 'PatchMonAgent'",
                        "agent_binary_path == expected_binary",
                        "agent_config_dir == expected_config",
                    ]
                }
            }
        )
    if facts.get("os_family") != "Windows" and expected:
        play[0]["tasks"].append(
            {
                "ansible.builtin.assert": {
                    "that": [
                        "agent_service_name == 'patchmon-agent'",
                        "agent_binary_path == '/usr/local/bin/patchmon-agent'",
                        "agent_config_dir == '/etc/patchmon'",
                    ]
                }
            }
        )
    path = tmp_path / "validate.json"
    path.write_text(json.dumps(play))
    # Defaults template PATCHMON_* from the environment. Clear them and pass
    # credentials through -e (highest precedence) so intentional empties stick.
    env = {
        key: value
        for key, value in __import__("os").environ.items()
        if not key.startswith("PATCHMON_")
    }
    extra = {
        "agent_state": state,
        "agent_server_url": vars_data["agent_server_url"],
        "agent_enrollment_key": vars_data["agent_enrollment_key"],
        "agent_enrollment_secret": vars_data["agent_enrollment_secret"],
    }
    result = subprocess.run(
        [
            executable,
            "-i",
            "localhost,",
            "-c",
            "local",
            str(path),
            "-e",
            json.dumps(extra),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert (result.returncode == 0) is expected, result.stdout + result.stderr

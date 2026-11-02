"""Run the agent role in check mode without credentials or a managed machine."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("existing_script", [False, True])
@pytest.mark.parametrize("valid_credentials", [False, True])
def test_install_check_mode(tmp_path, existing_script, valid_credentials):
    executable = shutil.which("ansible-playbook")
    if not executable:
        pytest.skip("ansible-playbook is required")
    controller = tmp_path / "enroll.sh"
    staged = tmp_path / "staged.sh"
    marker = tmp_path / "executed"
    script = f"#!/bin/sh\ntouch '{marker}'\n"
    if existing_script:
        controller.write_text(script)
        controller.chmod(0o700)
    play = [
        {
            "name": "Check a clean agent installation",
            "hosts": "localhost",
            "gather_facts": False,
            "become": False,
            "vars": {
                "ansible_facts": {"os_family": "Debian"},
                "agent_state": "present",
                "agent_report": True,
                "agent_server_url": "http://127.0.0.1:1",
                "agent_enrollment_key": "test-key" if valid_credentials else "",
                "agent_enrollment_secret": "test-secret",
                "agent_verify_ssl": True,
                "agent_script_controller_path": str(controller),
                "agent_script_path": str(staged),
                "agent_service_name": "patchmon-check-mode-nonexistent-service",
            },
            "roles": ["patchmon.core.agent"],
        }
    ]
    path = tmp_path / "play.json"
    path.write_text(json.dumps(play))
    env = os.environ.copy()
    env.update(
        {
            "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg"),
            "ANSIBLE_COLLECTIONS_PATH": str(ROOT / ".collections"),
            "ANSIBLE_INVENTORY_ENABLED": "host_list",
            "ANSIBLE_NOCOLOR": "1",
        }
    )
    result = subprocess.run(
        [executable, "-i", "localhost,", "-c", "local", str(path), "--check"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    assert (result.returncode == 0) is valid_credentials, output
    if valid_credentials:
        assert "Installer changes cannot be predicted" in output
        assert "TASK [patchmon.core.agent : Fetch enrollment script" not in output
        assert "TASK [patchmon.core.agent : Ensure PatchMon agent service" not in output
        assert "TASK [patchmon.core.agent : Trigger PatchMon agent report" not in output
    else:
        assert "required when agent_state is present" in output
    assert not staged.exists()
    assert not marker.exists()
    assert controller.exists() is existing_script
    if existing_script:
        assert controller.read_text() == script

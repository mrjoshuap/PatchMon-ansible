"""Exercise role validation through Ansible without contacting a managed host."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "facts,state,expected",
    [
        ({"os_family": "Windows"}, "started", True),
        ({"os_family": "Windows"}, "stopped", True),
        ({"os_family": "Windows"}, "report", True),
        ({"os_family": "Windows"}, "present", False),
        ({"os_family": "Windows"}, "absent", False),
        ({}, "started", True),
        ({"os_family": "Debian"}, "started", True),
    ],
)
def test_agent_validation(tmp_path, facts, state, expected):
    executable = shutil.which("ansible-playbook")
    if not executable:
        pytest.skip("ansible-playbook is required")
    play = [
        {
            "hosts": "localhost",
            "gather_facts": False,
            "vars_files": [
                str(ROOT / "roles/agent/vars/main.yml"),
                str(ROOT / "roles/agent/defaults/main.yml"),
            ],
            "vars": {"ansible_facts": facts, "agent_state": state},
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
    result = subprocess.run(
        [
            executable,
            "-i",
            "localhost,",
            "-c",
            "local",
            str(path),
            "-e",
            json.dumps({"agent_state": state}),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (result.returncode == 0) is expected, result.stdout + result.stderr
    if not expected:
        assert "not implemented" in result.stdout

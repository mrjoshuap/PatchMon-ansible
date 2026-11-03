# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the host_agent_script module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

import pytest

from ansible_collections.patchmon.core.plugins.modules import host_agent_script as mod


def test_install_enrolls_and_writes_dest(monkeypatch, tmp_path):
    exits = {}
    dest = str(tmp_path / "install.ps1")
    seen = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "install",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": "ek",
                "enrollment_secret": "es",
                "friendly_name": "WIN-01",
                "machine_id": "guid-1",
                "host_id": None,
                "api_id": None,
                "api_key": None,
                "os": "windows",
                "force": True,
                "dest": dest,
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeEnrollment(object):
        def __init__(self, *args, **kwargs):
            pass

        def enroll(self, friendly_name, machine_id=None, host_id=None, metadata=None):
            seen["enroll"] = {
                "friendly_name": friendly_name,
                "machine_id": machine_id,
            }
            return {
                "host": {
                    "id": "host-1",
                    "api_id": "patchmon_abc",
                    "api_key": "secret-key",
                }
            }

    class FakeHostAgent(object):
        def __init__(self, *args, **kwargs):
            seen["agent_kwargs"] = kwargs

        def get_install_script(self, os_name="windows", force=False):
            seen["install"] = {"os_name": os_name, "force": force}
            return "# install\nWrite-Host ok\n"

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "PatchMonHostAgentClient", FakeHostAgent)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is True
    assert exits["dest"] == dest
    assert exits["host_id"] == "host-1"
    assert "script" not in exits
    assert "api_key" not in exits
    assert seen["enroll"]["machine_id"] == "guid-1"
    assert seen["agent_kwargs"]["api_id"] == "patchmon_abc"
    assert seen["install"]["force"] is True
    assert os.path.isfile(dest)
    assert "Write-Host ok" in open(dest, encoding="utf-8").read()


def test_install_with_existing_host_credentials_skips_enroll(monkeypatch, tmp_path):
    exits = {}
    dest = str(tmp_path / "install.ps1")
    seen = {"enroll_called": False}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "install",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": None,
                "enrollment_secret": None,
                "friendly_name": None,
                "machine_id": None,
                "host_id": None,
                "api_id": "patchmon_abc",
                "api_key": "secret-key",
                "os": "windows",
                "force": False,
                "dest": dest,
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeEnrollment(object):
        def __init__(self, *args, **kwargs):
            pass

        def enroll(self, *args, **kwargs):
            seen["enroll_called"] = True
            raise AssertionError("enroll should not run")

    class FakeHostAgent(object):
        def __init__(self, *args, **kwargs):
            pass

        def get_install_script(self, os_name="windows", force=False):
            return "# install\n"

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "PatchMonHostAgentClient", FakeHostAgent)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is True
    assert seen["enroll_called"] is False


def test_remove_writes_dest(monkeypatch, tmp_path):
    exits = {}
    dest = str(tmp_path / "remove.ps1")

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "remove",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": None,
                "enrollment_secret": None,
                "friendly_name": None,
                "machine_id": None,
                "host_id": None,
                "api_id": None,
                "api_key": None,
                "os": "windows",
                "force": False,
                "dest": dest,
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeHostAgent(object):
        def __init__(self, *args, **kwargs):
            assert kwargs.get("api_id") is None

        def get_remove_script(self, os_name="windows"):
            assert os_name == "windows"
            return "# remove\n"

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonHostAgentClient", FakeHostAgent)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is True
    assert exits["dest"] == dest
    assert open(dest, encoding="utf-8").read() == "# remove\n"

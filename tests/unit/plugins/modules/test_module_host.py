# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the host module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.core.plugins.modules import host as mod


def test_present_skips_when_host_listed(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "present",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": "ek",
                "enrollment_secret": "es",
                "friendly_name": "web1",
                "machine_id": None,
                "host_id": None,
                "metadata": None,
                "force_enroll": False,
                "api_url": "https://patchmon.example.com",
                "api_key": "ik",
                "api_secret": "is",
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeIntegration(object):
        def __init__(self, *args, **kwargs):
            pass

        def find_host(self, **kwargs):
            return {"id": "uuid-1", "friendly_name": "web1"}

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeIntegration)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is False
    assert exits["already_exists"] is True


def test_present_enrolls(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "present",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": "ek",
                "enrollment_secret": "es",
                "friendly_name": "web1",
                "machine_id": "mid",
                "host_id": None,
                "metadata": None,
                "force_enroll": True,
                "api_url": None,
                "api_key": None,
                "api_secret": None,
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

        def enroll(self, **kwargs):
            return {
                "message": "Host enrolled successfully",
                "host": {
                    "id": "uuid-1",
                    "friendly_name": "web1",
                    "api_id": "aid",
                    "api_key": "secret",
                },
            }

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is True
    assert exits["host"]["id"] == "uuid-1"


def test_absent_deletes(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "absent",
                "server_url": None,
                "enrollment_key": None,
                "enrollment_secret": None,
                "friendly_name": None,
                "machine_id": None,
                "host_id": "uuid-1",
                "metadata": None,
                "force_enroll": False,
                "api_url": "https://patchmon.example.com",
                "api_key": "ik",
                "api_secret": "is",
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeIntegration(object):
        def __init__(self, *args, **kwargs):
            pass

        def find_host(self, **kwargs):
            return {"id": "uuid-1"}

        def delete_host(self, host_id):
            return {"message": "deleted", "id": host_id}

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeIntegration)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is True
    assert exits["host"]["id"] == "uuid-1"


def test_present_updates_listed_host_without_enrolling(monkeypatch):
    exits = {}
    enrolled = {"called": False}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "present",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": "ek",
                "enrollment_secret": "es",
                "friendly_name": "web1",
                "friendly_name_update": None,
                "machine_id": None,
                "host_id": "uuid-1",
                "metadata": None,
                "force_enroll": False,
                "notes": "keep me",
                "auto_update": None,
                "host_down_alerts": None,
                "groups": None,
                "api_url": "https://patchmon.example.com",
                "api_key": "ik",
                "api_secret": "is",
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeIntegration(object):
        def __init__(self, *args, **kwargs):
            pass

        def find_host(self, **kwargs):
            return {"id": "uuid-1", "friendly_name": "web1"}

        def reconcile_host(self, host_id, check_mode=False, **managed):
            assert host_id == "uuid-1"
            assert check_mode is False
            assert managed["notes"] == "keep me"
            return {
                "changed": True,
                "updates": ["notes"],
                "diff": {"before": {"notes": ""}, "after": {"notes": "keep me"}},
            }

    class FakeEnrollment(object):
        def __init__(self, *args, **kwargs):
            enrolled["called"] = True

        def enroll(self, **kwargs):
            enrolled["called"] = True
            raise AssertionError("enroll should not run")

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeIntegration)
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert enrolled["called"] is False
    assert exits["changed"] is True
    assert exits["already_exists"] is True
    assert exits["updates"] == ["notes"]
    assert exits["diff"]["after"]["notes"] == "keep me"


def test_update_only_requires_host_id(monkeypatch):
    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = True
            self.params = {
                "state": "present",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": None,
                "enrollment_secret": None,
                "friendly_name": None,
                "friendly_name_update": None,
                "machine_id": None,
                "host_id": None,
                "metadata": None,
                "force_enroll": False,
                "notes": "x",
                "auto_update": None,
                "host_down_alerts": None,
                "groups": None,
                "api_url": "https://patchmon.example.com",
                "api_key": "ik",
                "api_secret": "is",
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            raise SystemExit(kwargs)

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit) as exc:
        mod.run_module()

    assert "host_id is required" in exc.value.args[0]["msg"]

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


def _enrollment_module(exits, failures):
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
            failures.update(kwargs)
            raise SystemExit(1)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    return FakeModule


def test_machine_id_match_without_host_id_fails(monkeypatch):
    exits = {}
    failures = {}

    class FakeEnrollment(object):
        def __init__(self, *args, **kwargs):
            pass

        def enroll(self, **kwargs):
            return {
                "error": "machine id matches an existing host",
                "code": "machine_id_match",
                "friendly_name": "web1",
            }

    monkeypatch.setattr(mod, "AnsibleModule", _enrollment_module(exits, failures))
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits == {}
    assert "Return host_id on enrollment machine_id_match" in failures["msg"]
    assert "https://feedback.patchmon.net/" in failures["msg"]
    assert failures["code"] == "machine_id_match"


def test_machine_id_match_with_host_id_exits(monkeypatch):
    exits = {}
    failures = {}

    class FakeEnrollment(object):
        def __init__(self, *args, **kwargs):
            pass

        def enroll(self, **kwargs):
            return {
                "error": "machine id matches an existing host",
                "code": "machine_id_match",
                "friendly_name": "web1",
                "host_id": "uuid-1",
            }

    monkeypatch.setattr(mod, "AnsibleModule", _enrollment_module(exits, failures))
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert failures == {}
    assert exits["changed"] is False
    assert exits["already_exists"] is True
    assert exits["host"]["id"] == "uuid-1"
    assert exits["conflict_code"] == "machine_id_match"


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


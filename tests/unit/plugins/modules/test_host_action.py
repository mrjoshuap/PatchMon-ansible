# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the host_action module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.patchmon.core.plugins.modules import host_action as mod


def test_check_mode_does_not_post(monkeypatch):
    posted = {"called": False}

    class FakeClient(object):
        def __init__(self, *args, **kwargs):
            pass

        def fetch_report(self, host_id):
            posted["called"] = True
            raise AssertionError(host_id)

    holder = {}

    class Factory(object):
        def __init__(self, *args, **kwargs):
            holder["module"] = self
            self.check_mode = True
            self.params = {
                "api_url": "https://patchmon.example.com",
                "api_key": "ik",
                "api_secret": "is",
                "verify_ssl": True,
                "timeout": 30,
                "host_id": "uuid-1",
                "action": "fetch_report",
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            holder["result"] = kwargs
            raise SystemExit(0)

    monkeypatch.setattr(mod, "AnsibleModule", Factory)
    monkeypatch.setattr(mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    try:
        mod.run_module()
    except SystemExit:
        pass

    assert posted["called"] is False
    assert holder["result"]["changed"] is True
    assert holder["result"]["action"] == "fetch_report"


def test_regenerate_credentials_returns_key(monkeypatch):
    holder = {}

    class Factory(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "api_url": "https://patchmon.example.com",
                "api_key": "ik",
                "api_secret": "is",
                "verify_ssl": True,
                "timeout": 30,
                "host_id": "uuid-1",
                "action": "regenerate_credentials",
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            holder["result"] = kwargs
            raise SystemExit(0)

    class FakeClient(object):
        def __init__(self, *args, **kwargs):
            pass

        def regenerate_credentials(self, host_id):
            assert host_id == "uuid-1"
            return {
                "apiId": "patchmon_abc",
                "apiKey": "secret-key",
                "warning": "Previous credentials are now invalid.",
            }

    monkeypatch.setattr(mod, "AnsibleModule", Factory)
    monkeypatch.setattr(mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    try:
        mod.run_module()
    except SystemExit:
        pass

    assert holder["result"]["changed"] is True
    assert holder["result"]["api_id"] == "patchmon_abc"
    assert holder["result"]["api_key"] == "secret-key"
    assert "invalid" in holder["result"]["warning"]
    assert "secret-key" not in holder["result"]["msg"]

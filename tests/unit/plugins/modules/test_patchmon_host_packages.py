# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for patchmon_host_packages module flow."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.patchmon.ansible.plugins.modules import (
    patchmon_host_packages as mod,
)


def test_run_module_counts_security_updates(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.params = {
                "api_url": "https://patchmon.example.com",
                "api_key": "key",
                "api_secret": "secret",
                "verify_ssl": True,
                "timeout": 30,
                "host_id": "host-1",
                "updates_only": True,
            }

        def fail_json(self, **kwargs):
            raise AssertionError("fail_json called: {0}".format(kwargs))

        def exit_json(self, **kwargs):
            exits.update(kwargs)

    class FakeClient(object):
        def __init__(self, *args, **kwargs):
            pass

        def get_host_packages(self, host_id, updates_only=False):
            assert host_id == "host-1"
            assert updates_only is True
            return {
                "host": {"id": host_id},
                "total": 3,
                "packages": [
                    {"name": "openssl", "is_security_update": True},
                    {"name": "curl", "is_security_update": False},
                    {"name": "bash", "is_security_update": True},
                ],
            }

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    mod.run_module()

    assert exits["changed"] is False
    assert exits["total"] == 3
    assert exits["security_updates_count"] == 2
    assert exits["host"]["id"] == "host-1"
    assert len(exits["packages"]) == 3

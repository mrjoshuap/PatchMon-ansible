# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for patchmon_host_info helpers and module flow."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.ansible.plugins.modules import (
    patchmon_host_info as mod,
)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (None, ["info"]),
        ([], ["info"]),
        (["stats"], ["info", "stats"]),
        (["info", "stats", "system"], ["info", "stats", "system"]),
        (["all"], ["info", "stats", "system", "network", "integrations"]),
        (["stats", "stats", "network"], ["info", "stats", "network"]),
    ],
)
def test_normalize_subset(given, expected):
    assert mod._normalize_subset(given) == expected


def test_run_module_aggregates_subsets(monkeypatch):
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
                "gather_subset": ["info", "stats"],
            }

        def fail_json(self, **kwargs):
            raise AssertionError("fail_json called: {0}".format(kwargs))

        def exit_json(self, **kwargs):
            exits.update(kwargs)

    class FakeClient(object):
        def __init__(self, *args, **kwargs):
            pass

        def get_host_info(self, host_id):
            return {"id": host_id, "friendly_name": "web"}

        def get_host_stats(self, host_id):
            return {"updates_count": 2}

        def get_host_system(self, host_id):
            raise AssertionError("system should not be fetched")

        def get_host_network(self, host_id):
            raise AssertionError("network should not be fetched")

        def get_host_integrations(self, host_id):
            raise AssertionError("integrations should not be fetched")

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    mod.run_module()

    assert exits["changed"] is False
    assert exits["host"]["info"]["friendly_name"] == "web"
    assert exits["host"]["stats"]["updates_count"] == 2
    assert "system" not in exits["host"]

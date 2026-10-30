# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for patchmon_host_info helpers and module flow."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.core.plugins.modules import (
    host_info as mod,
)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (None, ["info"]),
        ([], ["info"]),
        (["stats"], ["info", "stats"]),
        (["info", "stats", "system"], ["info", "stats", "system"]),
        (
            ["all"],
            [
                "info",
                "stats",
                "system",
                "network",
                "integrations",
                "notes",
                "package_reports",
                "agent_queue",
            ],
        ),
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
                "limit": 10,
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

        def get_host_notes(self, host_id):
            raise AssertionError("notes should not be fetched")

        def get_host_package_reports(self, host_id, limit=None):
            raise AssertionError("package_reports should not be fetched")

        def get_host_agent_queue(self, host_id, limit=None):
            raise AssertionError("agent_queue should not be fetched")

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    mod.run_module()

    assert exits["changed"] is False
    assert exits["host"]["info"]["friendly_name"] == "web"
    assert exits["host"]["stats"]["updates_count"] == 2
    assert "system" not in exits["host"]
    assert "ansible_facts" not in exits


def test_run_module_fetches_reports_and_queue(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.params = {
                "api_url": "https://patchmon.example.com",
                "api_key": "key",
                "api_secret": "secret",
                "verify_ssl": True,
                "timeout": 30,
                "host_id": "host-9",
                "gather_subset": ["package_reports", "agent_queue", "notes"],
                "limit": 3,
            }

        def fail_json(self, **kwargs):
            raise AssertionError("fail_json called: {0}".format(kwargs))

        def exit_json(self, **kwargs):
            exits.update(kwargs)

    class FakeClient(object):
        def __init__(self, *args, **kwargs):
            pass

        def get_host_info(self, host_id):
            return {"id": host_id}

        def get_host_notes(self, host_id):
            return {"notes": "maintenance window"}

        def get_host_package_reports(self, host_id, limit=None):
            assert limit == 3
            return {"reports": [{"status": "success"}]}

        def get_host_agent_queue(self, host_id, limit=None):
            assert limit == 3
            return {"queue_status": {"failed": 0}}

        def get_host_stats(self, host_id):
            raise AssertionError("stats should not be fetched")

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

    assert "ansible_facts" not in exits
    assert exits["host"]["notes"]["notes"] == "maintenance window"
    assert exits["host"]["package_reports"]["reports"][0]["status"] == "success"
    assert exits["host"]["agent_queue"]["queue_status"]["failed"] == 0
    assert "info" in exits["host"]


def test_build_patchmon_facts_merges_identity_and_stats():
    facts = mod._build_patchmon_facts(
        "host-1",
        {
            "info": {
                "id": "other",
                "hostname": "web01.example.com",
                "friendly_name": "web",
                "ip": "192.168.1.100",
                "os_type": "Ubuntu",
                "os_version": "24.04",
                "status": "active",
            },
            "stats": {
                "updates_count": 15,
                "security_updates_count": 3,
                "total_packages": 342,
                "outdated_packages": 15,
                "hostname": "do-not-override",
            },
            "system": {"needs_reboot": True, "kernel_version": "6.8.0"},
        },
    )

    assert facts["id"] == "host-1"
    assert facts["hostname"] == "web01.example.com"
    assert facts["friendly_name"] == "web"
    assert facts["ip"] == "192.168.1.100"
    assert facts["os_type"] == "Ubuntu"
    assert facts["os_version"] == "24.04"
    assert facts["status"] == "active"
    assert facts["updates_count"] == 15
    assert facts["security_updates_count"] == 3
    assert facts["total_packages"] == 342
    assert facts["outdated_packages"] == 15
    assert facts["needs_reboot"] is True
    assert "kernel_version" not in facts
    assert "patchmon_needs_reboot" not in facts


def test_updates_count_preserves_explicit_values_and_absence():
    facts = mod._build_patchmon_facts(
        "host-1", {"stats": {"outdated_packages": 7, "updates_count": 0}}
    )
    assert facts["updates_count"] == 0
    assert facts["outdated_packages"] == 7
    for stats in ({}, {"outdated_packages": None}):
        assert "updates_count" not in mod._build_patchmon_facts(
            "host-1", {"stats": stats}
        )


@pytest.mark.parametrize("counts", [(0, 0, 986), (7, 2, 20)])
def test_run_module_inject_facts(monkeypatch, counts):
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
                "gather_subset": ["info", "stats", "system"],
                "limit": 10,
                "inject_facts": True,
            }

        def fail_json(self, **kwargs):
            raise AssertionError("fail_json called: {0}".format(kwargs))

        def exit_json(self, **kwargs):
            exits.update(kwargs)

    class FakeClient(object):
        def __init__(self, *args, **kwargs):
            pass

        def get_host_info(self, host_id):
            return {"hostname": "web01", "friendly_name": "web"}

        def get_host_stats(self, host_id):
            return {
                "outdated_packages": counts[0],
                "security_updates": counts[1],
                "total_installed_packages": counts[2],
                "last_update": "2026-02-12T10:30:00.000Z",
            }

        def get_host_system(self, host_id):
            return {"needs_reboot": False}

        def get_host_network(self, host_id):
            raise AssertionError("network should not be fetched")

        def get_host_integrations(self, host_id):
            raise AssertionError("integrations should not be fetched")

        def get_host_notes(self, host_id):
            raise AssertionError("notes should not be fetched")

        def get_host_package_reports(self, host_id, limit=None):
            raise AssertionError("package_reports should not be fetched")

        def get_host_agent_queue(self, host_id, limit=None):
            raise AssertionError("agent_queue should not be fetched")

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    mod.run_module()

    assert exits["host"]["stats"]["outdated_packages"] == counts[0]
    assert "updates_count" not in exits["host"]["stats"]
    patchmon = exits["ansible_facts"]["patchmon"]
    assert patchmon["id"] == "host-1"
    assert patchmon["friendly_name"] == "web"
    assert patchmon["updates_count"] == counts[0]
    assert patchmon["outdated_packages"] == counts[0]
    assert patchmon["security_updates"] == counts[1]
    assert patchmon["total_installed_packages"] == counts[2]
    assert patchmon["last_update"] == "2026-02-12T10:30:00.000Z"
    assert patchmon["needs_reboot"] is False
    assert "patchmon_updates_count" not in patchmon

# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the PatchMon dynamic inventory plugin helpers."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.patchmon.core.plugins.inventory import (
    inventory as inv,
)


class FakeInventory(object):
    def __init__(self):
        self.hosts = {}
        self.groups = set()
        self.membership = {}
        self.group_vars = {}

    def add_host(self, name, group=None):
        self.hosts.setdefault(name, {})
        if group:
            self.membership.setdefault(group, set()).add(name)

    def add_group(self, name):
        self.groups.add(name)
        return name

    def set_variable(self, entity, key, value):
        if entity in self.groups and entity not in self.hosts:
            self.group_vars.setdefault(entity, {})[key] = value
            return
        self.hosts.setdefault(entity, {})[key] = value


class FakePlugin(inv.InventoryModule):
    def __init__(self):
        self.inventory = FakeInventory()
        self._options = {
            "include_stats": True,
            "auto_groups": True,
            "inventory_hostname_prefer": "hostname",
            "compose": {},
            "groups": {},
            "keyed_groups": {},
            "strict": False,
        }

    def get_option(self, option):
        return self._options.get(option)

    def _sanitize_group_name(self, name):
        return name

    def _set_composite_vars(self, *args, **kwargs):
        return None

    def _add_host_to_composed_groups(self, *args, **kwargs):
        return None

    def _add_host_to_keyed_groups(self, *args, **kwargs):
        return None


SAMPLE_HOST = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "friendly_name": "web-server-01",
    "hostname": "web01.example.com",
    "ip": "192.168.1.100",
    "host_groups": [{"id": "g1", "name": "Production"}],
    "os_type": "Ubuntu",
    "os_version": "24.04 LTS",
    "last_update": "2026-02-12T10:30:00.000Z",
    "status": "active",
    "effective_status": "active",
    "reporting_state": "reporting",
    "update_state": "security_required",
    "needs_reboot": True,
    "updates_count": 15,
    "security_updates_count": 3,
    "total_packages": 342,
}


def test_populate_sets_stats_hostvars_and_auto_groups():
    plugin = FakePlugin()
    plugin._populate([SAMPLE_HOST])

    hostvars = plugin.inventory.hosts["web01.example.com"]
    assert hostvars["ansible_host"] == "192.168.1.100"
    assert hostvars["patchmon_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert hostvars["patchmon_friendly_name"] == "web-server-01"
    assert hostvars["patchmon_needs_reboot"] is True
    assert hostvars["patchmon_update_state"] == "security_required"
    assert hostvars["patchmon_security_updates_count"] == 3
    assert hostvars["patchmon_os_type"] == "Ubuntu"
    assert hostvars["patchmon_os_version"] == "24.04 LTS"
    assert hostvars["patchmon_status"] == "active"
    assert hostvars["patchmon_updates_count"] == 15
    assert hostvars["patchmon_total_packages"] == 342
    assert hostvars["patchmon_last_update"] == "2026-02-12T10:30:00.000Z"

    assert "patchmon_production" in plugin.inventory.groups
    assert hostvars["patchmon_groups"] == [
        {
            "id": "g1",
            "name": "Production",
            "ansible_group": "patchmon_production",
        }
    ]
    assert plugin.inventory.group_vars["patchmon_production"][
        "patchmon_group_name"
    ] == ("Production")
    assert (
        plugin.inventory.group_vars["patchmon_production"]["patchmon_group_id"] == "g1"
    )
    assert "patchmon_needs_reboot" in plugin.inventory.groups
    assert "patchmon_security_required" in plugin.inventory.groups
    assert "patchmon_os_ubuntu" in plugin.inventory.groups
    assert "web01.example.com" in plugin.inventory.membership["patchmon_needs_reboot"]


def test_targeting_scope_omits_telemetry_and_keeps_groups():
    plugin = FakePlugin()
    plugin._options["stats_var_scope"] = "targeting"
    plugin._populate([SAMPLE_HOST])

    hostvars = plugin.inventory.hosts["web01.example.com"]
    assert hostvars["patchmon_needs_reboot"] is True
    assert hostvars["patchmon_update_state"] == "security_required"
    assert hostvars["patchmon_security_updates_count"] == 3
    assert hostvars["patchmon_os_type"] == "Ubuntu"
    assert hostvars["patchmon_effective_status"] == "active"
    assert hostvars["patchmon_reporting_state"] == "reporting"
    assert hostvars["patchmon_id"] == "550e8400-e29b-41d4-a716-446655440000"
    for key in (
        "patchmon_os_version",
        "patchmon_last_update",
        "patchmon_status",
        "patchmon_updates_count",
        "patchmon_total_packages",
    ):
        assert key not in hostvars
    assert "patchmon_needs_reboot" in plugin.inventory.groups
    assert "patchmon_security_required" in plugin.inventory.groups
    assert "patchmon_os_ubuntu" in plugin.inventory.groups


def test_inventory_hostname_prefer_friendly_name():
    plugin = FakePlugin()
    plugin._options["inventory_hostname_prefer"] = "friendly_name"
    plugin._populate([SAMPLE_HOST])

    assert "web-server-01" in plugin.inventory.hosts
    assert plugin.inventory.hosts["web-server-01"]["patchmon_hostname"] == (
        "web01.example.com"
    )


def test_auto_groups_disabled():
    plugin = FakePlugin()
    plugin._options["auto_groups"] = False
    plugin._populate([SAMPLE_HOST])

    assert "patchmon_production" in plugin.inventory.groups
    assert "patchmon_needs_reboot" not in plugin.inventory.groups


def test_unprefixed_compose_aliases():
    """Raw ip/hostname/friendly_name remain for Constructable compose."""
    plugin = FakePlugin()
    plugin._populate([SAMPLE_HOST])

    hostvars = plugin.inventory.hosts["web01.example.com"]
    assert hostvars["ip"] == "192.168.1.100"
    assert hostvars["hostname"] == "web01.example.com"
    assert hostvars["friendly_name"] == "web-server-01"
    assert hostvars["patchmon_ip"] == "192.168.1.100"


def test_host_group_space_becomes_patchmon_slug():
    plugin = FakePlugin()
    host = dict(SAMPLE_HOST)
    host["host_groups"] = [{"id": "g-space", "name": "No Reboot"}]
    plugin._populate([host])

    assert "patchmon_no_reboot" in plugin.inventory.groups
    assert plugin.inventory.group_vars["patchmon_no_reboot"]["patchmon_group_name"] == (
        "No Reboot"
    )


def test_space_and_underscore_groups_are_disambiguated_by_id():
    plugin = FakePlugin()
    host = dict(SAMPLE_HOST)
    host["host_groups"] = [
        {"id": "aaa-111", "name": "No Reboot"},
        {"id": "bbb-222", "name": "No_Reboot"},
    ]
    plugin._populate([host])

    assert "patchmon_no_reboot_aaa_111" in plugin.inventory.groups
    assert "patchmon_no_reboot_bbb_222" in plugin.inventory.groups
    names = {
        item["name"]: item["ansible_group"]
        for item in plugin.inventory.hosts["web01.example.com"]["patchmon_groups"]
    }
    assert names["No Reboot"] == "patchmon_no_reboot_aaa_111"
    assert names["No_Reboot"] == "patchmon_no_reboot_bbb_222"

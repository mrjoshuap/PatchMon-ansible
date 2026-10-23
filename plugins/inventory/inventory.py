# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PatchMon Integration API dynamic inventory plugin."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: inventory
short_description: Dynamic inventory from the PatchMon Integration API
version_added: "1.0.0"
description:
  - Queries the PatchMon Integration API hosts endpoint and builds an Ansible inventory.
  - Optionally requests C(include=stats) for reboot, update, security, OS, and reporting metadata.
  - Supports constructed inventory features (compose, groups, keyed_groups).
  - Prefer namespaced C(patchmon_*) hostvars. Unprefixed C(ip), C(hostname), and C(friendly_name)
    are also set as compose aliases and may collide with user variables.
  - O(stats_var_scope=targeting) omits telemetry hostvars. Those fields belong in
    C(ansible_facts.patchmon) from C(patchmon.core.host_info) with O(patchmon.core.host_info#module:inject_facts=true),
    not as a second copy of the same C(patchmon_*) names.
  - PatchMon host groups become Ansible groups named C(patchmon_<slug>). Spaces and
    other characters Ansible rejects are replaced with C(_), then lowercased, so
    C(No Reboot) becomes C(patchmon_no_reboot). When two groups share that slug,
    or the slug is a stats auto-group, the group id is appended. The original
    name and id are on each host as C(patchmon_groups) and as group vars
    C(patchmon_group_name) / C(patchmon_group_id).
extends_documentation_fragment:
  - constructed
  - inventory_cache
  - patchmon.core.auth_plugin
options:
  plugin:
    description: FQCN of this inventory plugin.
    required: true
    choices: ["patchmon.core.inventory"]
  include_stats:
    description:
      - When true, call the hosts endpoint with C(?include=stats) and expose PatchMon
        metadata as C(patchmon_*) host variables.
      - Enables built-in auto groups unless O(auto_groups) is false.
      - O(stats_var_scope) selects which of those host variables are set.
        Auto groups still use the API payload.
    type: bool
    default: false
    version_added: "2.0.0"
  stats_var_scope:
    description:
      - Which stats fields to copy onto the host when O(include_stats) is true.
      - C(all) sets every C(patchmon_*) stats hostvar.
      - C(targeting) sets only fields used to build groups or to gate plays
        (C(patchmon_needs_reboot), C(patchmon_update_state),
        C(patchmon_security_updates_count), C(patchmon_os_type),
        C(patchmon_effective_status), C(patchmon_reporting_state)).
      - Telemetry (C(patchmon_updates_count), C(patchmon_total_packages),
        C(patchmon_last_update), C(patchmon_os_version), C(patchmon_status))
        is omitted. Read it from C(patchmon.core.host_info) with
        O(patchmon.core.host_info#module:inject_facts=true) as C(ansible_facts.patchmon).
      - C(compose), C(groups), and C(keyed_groups) expressions that reference
        an omitted hostvar require C(all).
    type: str
    default: all
    choices: [all, targeting]
    version_added: "2.0.0"
  hostgroup:
    description:
      - Optional PatchMon host group filter passed to the hosts list query.
      - Accepts a group id or the exact PatchMon name (spaces allowed).
      - C(No Reboot) and C(No_Reboot) are different groups. An Ansible
        C(patchmon_<slug>) token is not translated. There is no Integration
        group catalog.
      - Multiple values may be provided as a list (OR logic on the API).
    type: raw
    version_added: "2.0.0"
  auto_groups:
    description:
      - When true and O(include_stats) is enabled, create derived groups such as
        C(patchmon_needs_reboot) and C(patchmon_security_required).
    type: bool
    default: true
    version_added: "2.0.0"
  inventory_hostname_prefer:
    description:
      - Which API field to use as the Ansible inventory hostname.
      - The unused field is still exposed as a host variable.
    type: str
    default: hostname
    choices: [hostname, friendly_name]
    version_added: "2.0.0"
requirements:
  - requests >= 2.25.1
author:
  - Steve Libonati <stevelibonati@yahoo.com>
  - mrjoshuap
"""

EXAMPLES = r"""
# Minimal inventory. Export PATCHMON_SERVER_URL, PATCHMON_API_KEY, and
# PATCHMON_API_SECRET. Omit them here. Inventory sources are not templated,
# so lookup() in api_url, api_key, or api_secret is not expanded.
# PATCHMON_API_URL or api_url overrides the derived hosts URL. Setting either
# directly is discouraged.
plugin: patchmon.core.inventory
verify_ssl: true

# Rich metadata with auto groups and constructed selection.
# compose, groups, and keyed_groups are expressions the plugin evaluates.
plugin: patchmon.core.inventory
include_stats: true
auto_groups: true
compose:
  patchmon_has_security_updates: patchmon_security_updates_count | int > 0
keyed_groups:
  - key: patchmon_update_state
    prefix: patchmon_update_state
  - key: patchmon_os_type
    prefix: patchmon_os_type
groups:
  patchmon_reboot_and_security: patchmon_needs_reboot and patchmon_security_updates_count | int > 0
"""

import re

from ansible.errors import AnsibleParserError
from ansible.module_utils.common.text.converters import to_native, to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ansible_collections.patchmon.core.plugins.module_utils.group_names import (
    GroupNameError,
    assign_ansible_group_names,
    group_key,
)
from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    PatchMonAPIError,
    PatchMonClient,
)

# Stats fields copied onto hosts when include_stats is true.
# Telemetry keys are omitted when stats_var_scope is targeting. Groups are
# still built from the API payload, not from the exported hostvars.
_STATS_HOSTVARS = (
    ("os_type", "patchmon_os_type"),
    ("os_version", "patchmon_os_version"),
    ("last_update", "patchmon_last_update"),
    ("status", "patchmon_status"),
    ("effective_status", "patchmon_effective_status"),
    ("reporting_state", "patchmon_reporting_state"),
    ("update_state", "patchmon_update_state"),
    ("needs_reboot", "patchmon_needs_reboot"),
    ("updates_count", "patchmon_updates_count"),
    ("security_updates_count", "patchmon_security_updates_count"),
    ("total_packages", "patchmon_total_packages"),
)

_TELEMETRY_STATS_KEYS = frozenset(
    ("os_version", "last_update", "status", "updates_count", "total_packages")
)

_UPDATE_STATE_GROUPS = {
    "security_required": "patchmon_security_required",
    "updates_pending": "patchmon_updates_pending",
    "up_to_date": "patchmon_up_to_date",
}

_REPORTING_STATE_GROUPS = {
    "stale": "patchmon_stale",
    "overdue": "patchmon_overdue",
}


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """PatchMon Integration API inventory plugin."""

    NAME = "patchmon.core.inventory"

    def verify_file(self, path):
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith((".yaml", ".yml")):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        if not HAS_REQUESTS:
            raise AnsibleParserError(
                "patchmon.core requires the Python 'requests' library"
            )

        self._read_config_data(path)

        cache_key = self.get_cache_key(path)
        user_cache_setting = self.get_option("cache")
        attempt_to_read_cache = user_cache_setting and cache
        cache_needs_update = user_cache_setting and not cache

        results = None
        if attempt_to_read_cache:
            try:
                results = self._cache[cache_key]
            except KeyError:
                cache_needs_update = True

        if results is None:
            results = self._fetch_hosts()
            if cache_needs_update or (user_cache_setting and cache):
                self._cache[cache_key] = results

        self._populate(results)

    def _fetch_hosts(self):
        try:
            client = PatchMonClient(
                api_url=self.get_option("api_url"),
                api_key=self.get_option("api_key"),
                api_secret=self.get_option("api_secret"),
                verify_ssl=self.get_option("verify_ssl"),
                timeout=self.get_option("timeout"),
            )
            hostgroup = self.get_option("hostgroup")
            if hostgroup:
                hostgroup = client.resolve_hostgroup_filter(hostgroup)
            payload = client.get_hosts(
                include_stats=self.get_option("include_stats"),
                hostgroup=hostgroup,
            )
        except PatchMonAPIError as exc:
            raise AnsibleParserError(
                "patchmon.core: {0}".format(to_native(exc))
            ) from exc

        return payload.get("hosts", [])

    def _populate(self, hosts):
        strict = self.get_option("strict")
        include_stats = self.get_option("include_stats")
        auto_groups = self.get_option("auto_groups") and include_stats
        prefer = self.get_option("inventory_hostname_prefer")

        catalog = {}
        for entry in hosts:
            if not isinstance(entry, dict):
                continue
            for row in _host_group_rows(entry):
                catalog[group_key(row)] = row
        try:
            assigned = assign_ansible_group_names(catalog.values())
        except GroupNameError as exc:
            raise AnsibleParserError(
                "patchmon.core: {0}".format(to_native(exc))
            ) from exc
        for key, row in catalog.items():
            ansible_name = self._sanitize_group_name(assigned[key])
            self.inventory.add_group(ansible_name)
            if row.get("id"):
                self.inventory.set_variable(
                    ansible_name, "patchmon_group_id", row["id"]
                )
            self.inventory.set_variable(
                ansible_name, "patchmon_group_name", row["name"]
            )

        for entry in hosts:
            if not isinstance(entry, dict):
                continue

            hostname = entry.get("hostname")
            friendly = entry.get("friendly_name")

            if prefer == "friendly_name":
                name = friendly or hostname
            else:
                name = hostname or friendly

            if not name:
                continue
            name = to_text(name)

            self.inventory.add_host(name)

            hostvars = self._build_hostvars(entry)
            membership = []
            for row in _host_group_rows(entry):
                ansible_name = self._sanitize_group_name(assigned[group_key(row)])
                membership.append(
                    {
                        "id": row.get("id"),
                        "name": row["name"],
                        "ansible_group": ansible_name,
                    }
                )
                self._add_to_group(name, ansible_name)
            membership.sort(key=lambda item: (item["name"], item.get("id") or ""))
            hostvars["patchmon_groups"] = membership
            for key, value in hostvars.items():
                self.inventory.set_variable(name, key, value)

            if auto_groups:
                self._add_auto_groups(name, entry)

            self._set_composite_vars(
                self.get_option("compose"), hostvars, name, strict=strict
            )
            self._add_host_to_composed_groups(
                self.get_option("groups"), hostvars, name, strict=strict
            )
            self._add_host_to_keyed_groups(
                self.get_option("keyed_groups"), hostvars, name, strict=strict
            )

    def _build_hostvars(self, entry):
        hostvars = {}

        hostname = entry.get("hostname")
        friendly = entry.get("friendly_name")
        host_id = entry.get("id")
        addr = entry.get("ip")

        if addr:
            hostvars["ansible_host"] = to_text(addr)
            hostvars["patchmon_ip"] = to_text(addr)

        if host_id is not None:
            hostvars["patchmon_id"] = to_text(host_id)

        if hostname:
            hostvars["patchmon_hostname"] = to_text(hostname)
        if friendly:
            hostvars["patchmon_friendly_name"] = to_text(friendly)

        if self.get_option("include_stats"):
            for api_key, var_name in _stats_fields(self.get_option("stats_var_scope")):
                if api_key in entry and entry[api_key] is not None:
                    value = entry[api_key]
                    if isinstance(value, bool) or isinstance(value, (int, float)):
                        hostvars[var_name] = value
                    else:
                        hostvars[var_name] = to_text(value)

        # Raw API fields useful for compose expressions before namespaced vars exist.
        hostvars["ip"] = to_text(addr) if addr else None
        if hostname:
            hostvars["hostname"] = to_text(hostname)
        if friendly:
            hostvars["friendly_name"] = to_text(friendly)

        return hostvars

    def _add_auto_groups(self, name, entry):
        if entry.get("needs_reboot") is True:
            self._add_to_group(name, "patchmon_needs_reboot")

        update_state = entry.get("update_state")
        if update_state in _UPDATE_STATE_GROUPS:
            self._add_to_group(name, _UPDATE_STATE_GROUPS[update_state])

        reporting_state = entry.get("reporting_state")
        if reporting_state in _REPORTING_STATE_GROUPS:
            self._add_to_group(name, _REPORTING_STATE_GROUPS[reporting_state])

        if entry.get("effective_status") == "inactive":
            self._add_to_group(name, "patchmon_inactive")

        os_type = entry.get("os_type")
        if os_type:
            slug = re.sub(r"[^\w]", "_", to_text(os_type)).strip("_").lower()
            if slug:
                self._add_to_group(name, "patchmon_os_{0}".format(slug))

    def _add_to_group(self, host, group_name):
        group_name = self._sanitize_group_name(group_name)
        self.inventory.add_group(group_name)
        self.inventory.add_host(host, group=group_name)


def _stats_fields(scope):
    if scope == "targeting":
        return tuple(
            item for item in _STATS_HOSTVARS if item[0] not in _TELEMETRY_STATS_KEYS
        )
    return _STATS_HOSTVARS


def _host_group_rows(entry):
    rows = []
    for group_entry in entry.get("host_groups") or []:
        if not isinstance(group_entry, dict):
            continue
        name = group_entry.get("name")
        if name is None or to_text(name).strip() == "":
            continue
        row = {"name": to_text(name)}
        if group_entry.get("id"):
            row["id"] = to_text(group_entry.get("id"))
        rows.append(row)
    return rows

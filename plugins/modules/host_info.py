#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host_info
short_description: Gather PatchMon host information
version_added: "2.0.0"
description:
  - Retrieves detailed information for a PatchMon host via the Integration API.
  - Optionally aggregates info, stats, system, network, integrations, notes,
    package_reports, and agent_queue endpoints.
  - O(inject_facts) adds C(ansible_facts.patchmon) (identity plus stats, no
    C(patchmon_) prefix). It does not set flat C(patchmon_*) facts.
  - Requires Integration API scope C(host:get).
extends_documentation_fragment:
  - patchmon.core.auth
options:
  host_id:
    description: PatchMon host UUID.
    type: str
    required: true
  gather_subset:
    description:
      - Which host detail endpoints to query.
      - C(info) is always included.
    type: list
    elements: str
    default: [info, stats, system]
    choices:
      - info
      - stats
      - system
      - network
      - integrations
      - notes
      - package_reports
      - agent_queue
      - all
  limit:
    description:
      - Maximum number of package reports or agent-queue jobs to return.
      - Sent as the C(limit) query parameter for C(package_reports) and
        C(agent_queue) only. The PatchMon default is 10.
    type: int
    default: 10
  inject_facts:
    description:
      - When true, also return C(ansible_facts.patchmon).
      - Keys are unprefixed. Identity comes from the C(info) subset
        (C(id), C(hostname), C(friendly_name), C(ip)).
      - Stats fields are taken from the gathered C(info), C(stats), and
        C(system) subsets. Every other key on the stats payload is included.
      - Flat C(patchmon_*) facts are not set, so inventory hostvars of those
        names are left alone.
    type: bool
    default: false
    version_added: "2.0.0"
author:
  - mrjoshuap
requirements:
  - requests >= 2.25.1
"""

EXAMPLES = r"""
- name: Gather PatchMon host info and system details
  patchmon.core.host_info:
    api_url: "{{ patchmon_api_url }}"
    api_key: "{{ patchmon_api_key }}"
    api_secret: "{{ patchmon_api_secret }}"
    host_id: "{{ patchmon_id }}"
    gather_subset:
      - info
      - stats
      - system
  delegate_to: localhost
  register: patchmon_info

- name: Publish identity and stats as nested facts
  patchmon.core.host_info:
    api_url: "{{ patchmon_api_url }}"
    api_key: "{{ patchmon_api_key }}"
    api_secret: "{{ patchmon_api_secret }}"
    host_id: "{{ patchmon_id }}"
    gather_subset:
      - info
      - stats
      - system
    inject_facts: true
  delegate_to: localhost
"""

RETURN = r"""
host:
  description: Aggregated PatchMon host details keyed by subset name.
  returned: success
  type: dict
  contains:
    info:
      description: Response from C(/hosts/:id/info).
      type: dict
    stats:
      description: Response from C(/hosts/:id/stats).
      type: dict
    system:
      description: Response from C(/hosts/:id/system).
      type: dict
    network:
      description: Response from C(/hosts/:id/network).
      type: dict
    integrations:
      description: Response from C(/hosts/:id/integrations).
      type: dict
    notes:
      description: Response from C(/hosts/:id/notes).
      type: dict
    package_reports:
      description: Response from C(/hosts/:id/package_reports).
      type: dict
    agent_queue:
      description: Response from C(/hosts/:id/agent_queue).
      type: dict
ansible_facts:
  description:
    - Present when O(inject_facts) is true.
    - C(patchmon) holds identity and stats without a C(patchmon_) prefix.
  returned: when O(inject_facts) is true
  type: dict
  contains:
    patchmon:
      description:
        - Identity (C(id), and C(hostname) / C(friendly_name) / C(ip) when the
          info subset includes them) plus stats fields such as C(needs_reboot),
          C(update_state), C(updates_count), C(os_version), and C(status).
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonClient,
)

_DETAIL_SUBSETS = [
    "info",
    "stats",
    "system",
    "network",
    "integrations",
    "notes",
    "package_reports",
    "agent_queue",
]

_FACT_IDENTITY_KEYS = ("hostname", "friendly_name", "ip")

# Same stats names the inventory plugin maps to patchmon_* hostvars.
_FACT_STATS_KEYS = (
    "os_type",
    "os_version",
    "last_update",
    "status",
    "effective_status",
    "reporting_state",
    "update_state",
    "needs_reboot",
    "updates_count",
    "security_updates_count",
    "total_packages",
)


def _as_dict(value):
    if isinstance(value, dict):
        return value
    return {}


def _build_patchmon_facts(host_id, gathered):
    """Identity plus stats for ansible_facts['patchmon'].

    Keys stay unprefixed so they do not override inventory hostvars such as
    patchmon_needs_reboot. Canonical stats are read from info, then stats,
    then system. Remaining stats payload keys are included as well.
    """
    gathered = _as_dict(gathered)
    info = _as_dict(gathered.get("info"))
    stats = _as_dict(gathered.get("stats"))
    system = _as_dict(gathered.get("system"))

    facts = {}
    for key in _FACT_IDENTITY_KEYS:
        if info.get(key) is not None:
            facts[key] = info[key]

    for source in (info, stats, system):
        for key in _FACT_STATS_KEYS:
            if source.get(key) is not None:
                facts[key] = source[key]

    for key, value in stats.items():
        if key in ("id",) or key in _FACT_IDENTITY_KEYS:
            continue
        if value is None or key in facts:
            continue
        facts[key] = value

    facts["id"] = host_id
    return facts


def _normalize_subset(gather_subset):
    if not gather_subset:
        return ["info"]
    if "all" in gather_subset:
        return list(_DETAIL_SUBSETS)
    subsets = []
    for item in gather_subset:
        if item not in subsets:
            subsets.append(item)
    if "info" not in subsets:
        subsets.insert(0, "info")
    return subsets


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type="str", required=True),
            api_key=dict(type="str", required=True, no_log=True),
            api_secret=dict(type="str", required=True, no_log=True),
            verify_ssl=dict(type="bool", default=True),
            timeout=dict(type="int", default=30),
            host_id=dict(type="str", required=True),
            gather_subset=dict(
                type="list",
                elements="str",
                default=["info", "stats", "system"],
                choices=_DETAIL_SUBSETS + ["all"],
            ),
            limit=dict(type="int", default=10),
            inject_facts=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    if not HAS_REQUESTS:
        module.fail_json(
            msg="The Python requests library is required",
            exception=str(REQUESTS_IMPORT_ERROR),
        )

    subsets = _normalize_subset(module.params["gather_subset"])
    host_id = module.params["host_id"]

    try:
        client = PatchMonClient(
            api_url=module.params["api_url"],
            api_key=module.params["api_key"],
            api_secret=module.params["api_secret"],
            verify_ssl=module.params["verify_ssl"],
            timeout=module.params["timeout"],
        )

        result = {}
        limit = module.params["limit"]
        fetchers = {
            "info": client.get_host_info,
            "stats": client.get_host_stats,
            "system": client.get_host_system,
            "network": client.get_host_network,
            "integrations": client.get_host_integrations,
            "notes": client.get_host_notes,
        }
        for subset in subsets:
            if subset == "package_reports":
                result[subset] = client.get_host_package_reports(host_id, limit=limit)
            elif subset == "agent_queue":
                result[subset] = client.get_host_agent_queue(host_id, limit=limit)
            else:
                result[subset] = fetchers[subset](host_id)
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc))

    payload = {"changed": False, "host": result}
    if module.params.get("inject_facts"):
        payload["ansible_facts"] = {"patchmon": _build_patchmon_facts(host_id, result)}
    module.exit_json(**payload)


def main():
    run_module()


if __name__ == "__main__":
    main()

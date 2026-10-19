#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: patchmon_host_info
short_description: Gather PatchMon host information
version_added: "1.1.0"
description:
  - Retrieves detailed information for a PatchMon host via the Integration API.
  - Optionally aggregates info, stats, system, network, and integrations endpoints.
options:
  api_url:
    description:
      - PatchMon hosts endpoint or instance root
        (for example C(https://patchmon.example.com/api/v1/api/hosts)).
    type: str
    required: true
  api_key:
    description: PatchMon API Token Key (Basic Auth username).
    type: str
    required: true
  api_secret:
    description: PatchMon API Token Secret (Basic Auth password).
    type: str
    required: true
    no_log: true
  verify_ssl:
    description: Verify the PatchMon TLS certificate.
    type: bool
    default: true
  timeout:
    description: HTTP timeout in seconds.
    type: int
    default: 30
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
    choices: [info, stats, system, network, integrations, all]
author:
  - mrjoshuap
requirements:
  - requests >= 2.25.1
"""

EXAMPLES = r"""
- name: Gather PatchMon host info and system details
  patchmon.ansible.patchmon_host_info:
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
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.ansible.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonClient,
)


def _normalize_subset(gather_subset):
    if not gather_subset:
        return ["info"]
    if "all" in gather_subset:
        return ["info", "stats", "system", "network", "integrations"]
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
                choices=["info", "stats", "system", "network", "integrations", "all"],
            ),
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
        fetchers = {
            "info": client.get_host_info,
            "stats": client.get_host_stats,
            "system": client.get_host_system,
            "network": client.get_host_network,
            "integrations": client.get_host_integrations,
        }
        for subset in subsets:
            result[subset] = fetchers[subset](host_id)
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=False, host=result)


def main():
    run_module()


if __name__ == "__main__":
    main()

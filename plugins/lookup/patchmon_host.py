# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lookup plugin for PatchMon host detail endpoints."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: patchmon_host
short_description: Look up PatchMon host details via the Integration API
version_added: "1.1.0"
description:
  - Queries a PatchMon per-host Integration API endpoint and returns the JSON payload.
extends_documentation_fragment:
  - patchmon.ansible.auth
options:
  _terms:
    description:
      - Host UUID to query.
    required: true
  resource:
    description: Per-host API resource to fetch.
    type: str
    default: info
    choices: [info, stats, system, network, integrations, packages, notes]
  updates_only:
    description: When O(resource=packages), only return packages with updates.
    type: bool
    default: false
author:
  - mrjoshuap
requirements:
  - requests >= 2.25.1
"""

EXAMPLES = r"""
- name: Get PatchMon system details for a host
  ansible.builtin.debug:
    msg: "{{ lookup('patchmon.ansible.patchmon_host', patchmon_id, resource='system') }}"

- name: List packages needing updates
  ansible.builtin.set_fact:
    pm_packages: "{{ lookup('patchmon.ansible.patchmon_host', patchmon_id, resource='packages', updates_only=true) }}"
"""

RETURN = r"""
_raw:
  description: JSON object returned by the selected PatchMon endpoint.
  type: list
  elements: dict
"""

from ansible.errors import AnsibleError, AnsibleOptionsError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

from ansible_collections.patchmon.ansible.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    PatchMonAPIError,
    PatchMonClient,
)

display = Display()


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if not HAS_REQUESTS:
            raise AnsibleError(
                "patchmon.ansible.patchmon_host requires the Python 'requests' library"
            )

        self.set_options(var_options=variables, direct=kwargs)

        if not terms:
            raise AnsibleOptionsError("One or more PatchMon host UUIDs are required")

        resource = self.get_option("resource")
        updates_only = self.get_option("updates_only")

        try:
            client = PatchMonClient(
                api_url=self.get_option("api_url"),
                api_key=self.get_option("api_key"),
                api_secret=self.get_option("api_secret"),
                verify_ssl=self.get_option("verify_ssl"),
                timeout=self.get_option("timeout"),
            )
        except PatchMonAPIError as exc:
            raise AnsibleError(str(exc)) from exc

        fetchers = {
            "info": client.get_host_info,
            "stats": client.get_host_stats,
            "system": client.get_host_system,
            "network": client.get_host_network,
            "integrations": client.get_host_integrations,
            "notes": client.get_host_notes,
        }

        results = []
        for host_id in terms:
            display.vvvv(
                "patchmon_host lookup: host_id={0} resource={1}".format(
                    host_id, resource
                )
            )
            try:
                if resource == "packages":
                    payload = client.get_host_packages(
                        host_id, updates_only=updates_only
                    )
                else:
                    payload = fetchers[resource](host_id)
            except PatchMonAPIError as exc:
                raise AnsibleError(str(exc)) from exc
            results.append(payload)

        return results

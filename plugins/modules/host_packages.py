#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host_packages
short_description: List packages for a PatchMon host
version_added: "2.0.0"
description:
  - Retrieves installed packages (or only packages with available updates) for a PatchMon host.
  - Requires Integration API scope C(host:get).
extends_documentation_fragment:
  - patchmon.ansible.auth
options:
  host_id:
    description: PatchMon host UUID.
    type: str
    required: true
  updates_only:
    description: When true, return only packages that have available updates.
    type: bool
    default: false
author:
  - mrjoshuap
requirements:
  - requests >= 2.25.1
"""

EXAMPLES = r"""
- name: List packages needing updates
  patchmon.ansible.host_packages:
    api_url: "{{ patchmon_api_url }}"
    api_key: "{{ patchmon_api_key }}"
    api_secret: "{{ patchmon_api_secret }}"
    host_id: "{{ patchmon_id }}"
    updates_only: true
  delegate_to: localhost
  register: pm_pkgs

- name: Show security updates
  ansible.builtin.debug:
    msg: "{{ item.name }}: {{ item.current_version }} -> {{ item.available_version }}"
  loop: "{{ pm_pkgs.packages | selectattr('is_security_update') | list }}"
  loop_control:
    label: "{{ item.name }}"
"""

RETURN = r"""
host:
  description: Host metadata returned with the package list.
  returned: success
  type: dict
packages:
  description: Package entries from PatchMon.
  returned: success
  type: list
  elements: dict
total:
  description: Number of packages returned.
  returned: success
  type: int
security_updates_count:
  description: Count of packages marked as security updates in the response.
  returned: success
  type: int
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.ansible.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonClient,
)


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type="str", required=True),
            api_key=dict(type="str", required=True, no_log=True),
            api_secret=dict(type="str", required=True, no_log=True),
            verify_ssl=dict(type="bool", default=True),
            timeout=dict(type="int", default=30),
            host_id=dict(type="str", required=True),
            updates_only=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    if not HAS_REQUESTS:
        module.fail_json(
            msg="The Python requests library is required",
            exception=str(REQUESTS_IMPORT_ERROR),
        )

    try:
        client = PatchMonClient(
            api_url=module.params["api_url"],
            api_key=module.params["api_key"],
            api_secret=module.params["api_secret"],
            verify_ssl=module.params["verify_ssl"],
            timeout=module.params["timeout"],
        )
        payload = client.get_host_packages(
            module.params["host_id"],
            updates_only=module.params["updates_only"],
        )
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc))

    packages = payload.get("packages") or []
    if not isinstance(packages, list):
        packages = []

    security_count = sum(
        1 for pkg in packages if isinstance(pkg, dict) and pkg.get("is_security_update")
    )

    module.exit_json(
        changed=False,
        host=payload.get("host") or {},
        packages=packages,
        total=payload.get("total", len(packages)),
        security_updates_count=security_count,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()

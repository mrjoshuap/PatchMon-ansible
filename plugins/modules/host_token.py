#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host_token
short_description: Manage PatchMon auto-enrollment tokens and installer scripts
version_added: "2.0.0"
description:
  - Creates or deletes Auto-Enrollment tokens (admin JWT), or fetches the
    enrollment installer script for an existing token.
  - Token create/delete requires a session JWT with Manage Settings permission
    (not an Integration API credential).
  - Script fetch uses Auto-Enrollment key/secret headers/query parameters.
  - WARNING - Creating tokens and fetching scripts exposes secrets. Prefer Vault
    or Controller credentials; never commit plaintext values.
options:
  state:
    description:
      - C(script) - download the enrollment bash script for an existing token.
      - C(present) - create an auto-enrollment token (requires O(admin_token)).
      - C(absent) - delete an auto-enrollment token by O(token_id) (requires O(admin_token)).
    type: str
    choices: [script, present, absent]
    default: script
  server_url:
    description:
      - Auto-enrollment URL or PatchMon instance root (for example C(https://patchmon.example.com)).
      - Prefer C(PATCHMON_SERVER_URL). The collection derives C(/api/v1/auto-enrollment) from it.
      - C(PATCHMON_ENROLLMENT_URL) overrides that derived URL. Setting it directly is discouraged.
    type: str
    required: true
  enrollment_key:
    description:
      - Existing auto-enrollment token key (for O(state=script)). This value is a secret.
    type: str
  enrollment_secret:
    description:
      - Existing auto-enrollment token secret (for O(state=script)). This value is a secret.
    type: str
  script_type:
    description: Enrollment script type query parameter.
    type: str
    default: direct-host
    choices: [direct-host, proxmox-lxc]
  force:
    description: Pass C(force=true) to the script endpoint.
    type: bool
    default: false
  dest:
    description:
      - Absolute path on the module host to write the enrollment script.
      - Required for O(state=script). Writing to a file avoids Ansible
        C(no_log) censoring the key/secret substrings inside a returned
        C(script) string (which becomes literal C(********)).
    type: path
    version_added: "2.0.1"
  admin_token:
    description:
      - Bearer JWT for admin token CRUD (Manage Settings). This value is a secret.
    type: str
  token_name:
    description: Name for a new auto-enrollment token (O(state=present)).
    type: str
  token_id:
    description: Token UUID to delete (O(state=absent)).
    type: str
  max_hosts_per_day:
    description: Daily enrollment limit for a new token.
    type: int
    default: 100
  default_host_group_id:
    description: Optional default host group UUID for a new token.
    type: str
  allowed_ip_ranges:
    description: Optional IP/CIDR allow list for a new token.
    type: list
    elements: str
  expires_at:
    description: Optional ISO-8601 expiration for a new token.
    type: str
  metadata:
    description: Optional metadata object for a new token.
    type: dict
  verify_ssl:
    description: Verify the PatchMon TLS certificate.
    type: bool
    default: true
  timeout:
    description: HTTP timeout in seconds.
    type: int
    default: 30
author:
  - mrjoshuap
requirements:
  - requests >= 2.25.1
"""

EXAMPLES = r"""
- name: Fetch direct-host enrollment script to a local file
  patchmon.core.host_token:
    state: script
    server_url: "{{ lookup('patchmon.core.endpoint', 'enrollment') }}"
    enrollment_key: "{{ lookup('env', 'PATCHMON_ENROLLMENT_KEY') }}"
    enrollment_secret: "{{ lookup('env', 'PATCHMON_ENROLLMENT_SECRET') }}"
    script_type: direct-host
    dest: /tmp/patchmon-enroll.sh
  delegate_to: localhost
  register: pm_script
  no_log: true

- name: Create an auto-enrollment token (admin JWT)
  patchmon.core.host_token:
    state: present
    server_url: "{{ lookup('patchmon.core.endpoint', 'enrollment') }}"
    admin_token: "{{ patchmon_admin_jwt }}"
    token_name: ansible-provisioning
    max_hosts_per_day: 50
  delegate_to: localhost
  register: pm_token
  no_log: true
"""

RETURN = r"""
dest:
  description: Path where the enrollment script was written (O(state=script)).
  returned: when state=script
  type: str
token:
  description: Created token object including secret (shown once).
  returned: when state=present
  type: dict
message:
  description: API message.
  type: str
"""

import os

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonAdminClient,
    PatchMonEnrollmentClient,
)


def _fetch_script(module):
    if not module.params.get("enrollment_key") or not module.params.get(
        "enrollment_secret"
    ):
        module.fail_json(
            msg="enrollment_key and enrollment_secret are required when state=script"
        )

    dest = module.params.get("dest")
    if not dest:
        module.fail_json(
            msg=(
                "dest is required when state=script. Write the script to a file so "
                "Ansible no_log does not censor key/secret substrings in a returned "
                "script string (see agent role install.yml)."
            )
        )

    if module.check_mode:
        module.exit_json(
            changed=False,
            dest=dest,
            msg="Would fetch enrollment script to {0}".format(dest),
        )

    client = PatchMonEnrollmentClient(
        server_url=module.params["server_url"],
        enrollment_key=module.params["enrollment_key"],
        enrollment_secret=module.params["enrollment_secret"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )
    try:
        script = client.get_script(
            script_type=module.params["script_type"],
            force=module.params["force"],
        )
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    dest_dir = os.path.dirname(dest)
    if dest_dir and not os.path.isdir(dest_dir):
        try:
            os.makedirs(dest_dir, mode=0o700)
        except OSError as exc:
            module.fail_json(msg="Unable to create directory for dest: {0}".format(exc))

    try:
        with open(dest, "w", encoding="utf-8") as handle:
            handle.write(script)
        os.chmod(dest, 0o700)
    except OSError as exc:
        module.fail_json(
            msg="Unable to write enrollment script to dest: {0}".format(exc)
        )

    # Do not return script body — no_log would replace key/secret with ********.
    module.exit_json(changed=False, dest=dest)


def _create_token(module):
    if not module.params.get("admin_token"):
        module.fail_json(msg="admin_token is required when state=present")
    if not module.params.get("token_name"):
        module.fail_json(msg="token_name is required when state=present")

    if module.check_mode:
        module.exit_json(
            changed=True,
            token={"token_name": module.params["token_name"]},
            msg="Would create auto-enrollment token",
        )

    client = PatchMonAdminClient(
        server_url=module.params["server_url"],
        admin_token=module.params["admin_token"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )
    try:
        payload = client.create_enrollment_token(
            token_name=module.params["token_name"],
            max_hosts_per_day=module.params["max_hosts_per_day"],
            default_host_group_id=module.params.get("default_host_group_id"),
            allowed_ip_ranges=module.params.get("allowed_ip_ranges"),
            expires_at=module.params.get("expires_at"),
            metadata=module.params.get("metadata"),
        )
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    module.exit_json(
        changed=True,
        token=(payload or {}).get("token") or payload,
        message=(payload or {}).get("message"),
        warning=(payload or {}).get("warning"),
    )


def _delete_token(module):
    if not module.params.get("admin_token"):
        module.fail_json(msg="admin_token is required when state=absent")
    if not module.params.get("token_id"):
        module.fail_json(msg="token_id is required when state=absent")

    if module.check_mode:
        module.exit_json(
            changed=True,
            token_id=module.params["token_id"],
            msg="Would delete auto-enrollment token",
        )

    client = PatchMonAdminClient(
        server_url=module.params["server_url"],
        admin_token=module.params["admin_token"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )
    try:
        payload = client.delete_enrollment_token(module.params["token_id"])
    except PatchMonAPIError as exc:
        if exc.status_code == 404:
            module.exit_json(
                changed=False,
                token_id=module.params["token_id"],
                msg="Token already absent",
            )
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    module.exit_json(
        changed=True,
        token_id=module.params["token_id"],
        message=(payload or {}).get("message"),
    )


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(
                type="str",
                default="script",
                choices=["script", "present", "absent"],
            ),
            server_url=dict(type="str", required=True),
            enrollment_key=dict(type="str", no_log=True),
            enrollment_secret=dict(type="str", no_log=True),
            script_type=dict(
                type="str",
                default="direct-host",
                choices=["direct-host", "proxmox-lxc"],
            ),
            force=dict(type="bool", default=False),
            dest=dict(type="path"),
            admin_token=dict(type="str", no_log=True),
            token_name=dict(type="str"),
            token_id=dict(type="str"),
            max_hosts_per_day=dict(type="int", default=100),
            default_host_group_id=dict(type="str"),
            allowed_ip_ranges=dict(type="list", elements="str"),
            expires_at=dict(type="str"),
            metadata=dict(type="dict"),
            verify_ssl=dict(type="bool", default=True),
            timeout=dict(type="int", default=30),
        ),
        supports_check_mode=True,
    )

    if not HAS_REQUESTS:
        module.fail_json(
            msg="The Python requests library is required",
            exception=str(REQUESTS_IMPORT_ERROR),
        )

    state = module.params["state"]
    if state == "script":
        _fetch_script(module)
    elif state == "present":
        _create_token(module)
    else:
        _delete_token(module)


def main():
    run_module()


if __name__ == "__main__":
    main()

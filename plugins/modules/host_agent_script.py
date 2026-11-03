#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host_agent_script
short_description: Fetch PatchMon per-host agent install or remove scripts
version_added: "2.0.8"
description:
  - Downloads the OS-specific agent installer or remover from
    C(/api/v1/hosts/install) or C(/api/v1/hosts/remove).
  - For O(state=install), enrolls the host through Auto-Enrollment (unless
    O(api_id)/O(api_key) are supplied), then writes the installer to O(dest).
  - Writing to a file avoids Ansible C(no_log) censoring secrets inside a
    returned script string.
  - Windows install mirrors the official Intune enroll then install-script flow.
options:
  state:
    description:
      - C(install) - enroll (optional) and download the agent installer.
      - C(remove) - download the agent removal script (no authentication).
    type: str
    choices: [install, remove]
    default: install
  server_url:
    description:
      - PatchMon instance root or auto-enrollment URL.
      - Prefer C(PATCHMON_SERVER_URL).
    type: str
    required: true
  enrollment_key:
    description:
      - Auto-Enrollment token key used when O(state=install) and host API
        credentials are not supplied.
    type: str
  enrollment_secret:
    description:
      - Auto-Enrollment token secret used when O(state=install) and host API
        credentials are not supplied.
    type: str
  friendly_name:
    description:
      - Host friendly name for Auto-Enrollment (O(state=install)).
    type: str
  machine_id:
    description:
      - Unique machine identifier for enrollment deduplication (Windows
        MachineGuid lowercased, or Linux C(/etc/machine-id)).
    type: str
  host_id:
    description:
      - Existing host UUID for re-enrollment recovery (O(state=install)).
    type: str
  api_id:
    description:
      - Existing host API id. When set with O(api_key), enrollment is skipped.
    type: str
  api_key:
    description:
      - Existing host API key. When set with O(api_id), enrollment is skipped.
    type: str
  os:
    description:
      - Operating system query parameter for the install or remove endpoint.
    type: str
    default: windows
    choices: [windows, linux, freebsd]
  force:
    description:
      - Pass C(force=true) to the install endpoint.
    type: bool
    default: false
  dest:
    description:
      - Absolute path on the module host to write the script.
      - Required. Do not return the script body through a register.
    type: path
    required: true
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
- name: Enroll a Windows host and write the installer to a local file
  patchmon.core.host_agent_script:
    state: install
    server_url: "{{ lookup('patchmon.core.endpoint', 'enrollment') }}"
    enrollment_key: "{{ lookup('env', 'PATCHMON_ENROLLMENT_KEY') }}"
    enrollment_secret: "{{ lookup('env', 'PATCHMON_ENROLLMENT_SECRET') }}"
    friendly_name: "{{ inventory_hostname }}"
    machine_id: "{{ windows_machine_guid }}"
    os: windows
    dest: /tmp/patchmon-install.ps1
  delegate_to: localhost
  register: pm_win_install
  no_log: true

- name: Fetch the Windows agent removal script
  patchmon.core.host_agent_script:
    state: remove
    server_url: "{{ lookup('patchmon.core.endpoint', 'enrollment') }}"
    os: windows
    dest: /tmp/patchmon-remove.ps1
  delegate_to: localhost
"""

RETURN = r"""
dest:
  description: Path where the script was written.
  returned: success
  type: str
host_id:
  description: PatchMon host id from enrollment (O(state=install)).
  returned: when enrollment ran successfully
  type: str
reenrolled:
  description: True when enrollment re-issued credentials for an existing host.
  returned: when applicable
  type: bool
"""

import os

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonEnrollmentClient,
    PatchMonHostAgentClient,
)

_MACHINE_ID_MATCH_FEEDBACK = (
    "Enrollment returned 409 machine_id_match without host_id. "
    "Create a PatchMon feedback request: https://feedback.patchmon.net/\n"
    "Subject: Return host_id on enrollment machine_id_match\n"
    "Description: POST /api/v1/auto-enrollment/enroll returns 409 "
    "machine_id_match with friendly_name and without host_id. The other 409 "
    "codes include host_id. Please include host_id on machine_id_match as well."
)


def _write_script(module, script, dest):
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
        module.fail_json(msg="Unable to write script to dest: {0}".format(exc))


def _credentials_from_enroll(module, payload, friendly_name):
    """Return (api_id, api_key, host_id, reenrolled) from an enroll payload."""
    if not isinstance(payload, dict):
        module.fail_json(msg="Unexpected enrollment response type")

    if payload.get("error"):
        code = payload.get("code")
        if code == "machine_id_match" and not payload.get("host_id"):
            extra = {key: value for key, value in payload.items() if key != "msg"}
            module.fail_json(msg=_MACHINE_ID_MATCH_FEEDBACK, **extra)
        module.fail_json(
            msg=payload.get("error") or "enrollment conflict",
            conflict_code=code,
            **{key: value for key, value in payload.items() if key != "msg"},
        )

    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    api_id = host.get("api_id")
    api_key = host.get("api_key")
    host_id = host.get("id") or payload.get("host_id")
    if not api_id or not api_key:
        module.fail_json(
            msg=(
                "Enrollment succeeded for {0} but the response did not include "
                "host.api_id and host.api_key needed to fetch the installer."
            ).format(friendly_name)
        )
    reenrolled = bool(payload.get("reenrolled"))
    return api_id, api_key, host_id, reenrolled


def _install(module):
    dest = module.params["dest"]
    api_id = module.params.get("api_id")
    api_key = module.params.get("api_key")
    host_id = module.params.get("host_id")
    reenrolled = False

    if module.check_mode:
        module.exit_json(
            changed=True,
            dest=dest,
            msg="Would enroll (if needed) and fetch the host install script to {0}".format(
                dest
            ),
        )

    if not (api_id and api_key):
        if not module.params.get("enrollment_key") or not module.params.get(
            "enrollment_secret"
        ):
            module.fail_json(
                msg=(
                    "enrollment_key and enrollment_secret are required when "
                    "api_id/api_key are not provided for state=install"
                )
            )
        friendly_name = module.params.get("friendly_name")
        if not friendly_name:
            module.fail_json(
                msg="friendly_name is required when enrolling for state=install"
            )
        if not module.params.get("machine_id"):
            module.fail_json(
                msg="machine_id is required when enrolling for state=install"
            )

        enroll_client = PatchMonEnrollmentClient(
            server_url=module.params["server_url"],
            enrollment_key=module.params["enrollment_key"],
            enrollment_secret=module.params["enrollment_secret"],
            verify_ssl=module.params["verify_ssl"],
            timeout=module.params["timeout"],
        )
        try:
            payload = enroll_client.enroll(
                friendly_name=friendly_name,
                machine_id=module.params.get("machine_id"),
                host_id=module.params.get("host_id") or None,
            )
        except PatchMonAPIError as exc:
            module.fail_json(msg=str(exc), status_code=exc.status_code)

        api_id, api_key, host_id, reenrolled = _credentials_from_enroll(
            module, payload, friendly_name
        )

    agent_client = PatchMonHostAgentClient(
        server_url=module.params["server_url"],
        api_id=api_id,
        api_key=api_key,
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )
    try:
        script = agent_client.get_install_script(
            os_name=module.params["os"],
            force=module.params["force"],
        )
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    _write_script(module, script, dest)
    result = {"changed": True, "dest": dest}
    if host_id:
        result["host_id"] = host_id
    if reenrolled:
        result["reenrolled"] = True
    module.exit_json(**result)


def _remove(module):
    dest = module.params["dest"]
    if module.check_mode:
        module.exit_json(
            changed=True,
            dest=dest,
            msg="Would fetch the host remove script to {0}".format(dest),
        )

    agent_client = PatchMonHostAgentClient(
        server_url=module.params["server_url"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )
    try:
        script = agent_client.get_remove_script(os_name=module.params["os"])
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    _write_script(module, script, dest)
    module.exit_json(changed=True, dest=dest)


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", default="install", choices=["install", "remove"]),
            server_url=dict(type="str", required=True),
            enrollment_key=dict(type="str", no_log=True),
            enrollment_secret=dict(type="str", no_log=True),
            friendly_name=dict(type="str"),
            machine_id=dict(type="str"),
            host_id=dict(type="str"),
            api_id=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            os=dict(
                type="str",
                default="windows",
                choices=["windows", "linux", "freebsd"],
            ),
            force=dict(type="bool", default=False),
            dest=dict(type="path", required=True),
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

    if module.params["state"] == "install":
        _install(module)
    else:
        _remove(module)


def main():
    run_module()


if __name__ == "__main__":
    main()

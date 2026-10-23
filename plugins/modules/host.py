#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host
short_description: Create or delete a PatchMon host entry
version_added: "2.0.0"
description:
  - Ensures a PatchMon host entry is present (auto-enrollment) or absent (Integration API delete).
  - C(state=present) uses the Auto-Enrollment API
    (C(X-Auto-Enrollment-Key) / C(X-Auto-Enrollment-Secret)), not Integration Basic Auth.
  - C(state=absent) uses the Integration API and requires scope C(host:delete).
  - Friendly name, notes, auto-update, host-down alerts, and group membership are session
    routes. This module does not change them.
  - A 409 C(machine_id_match) without C(host_id) fails with a PatchMon feedback draft.
    The same code with C(host_id) is treated as already present.
  - See U(https://patchmon.net/docs/patchmon-api-integrations-guide) and the
    Credentials chapter of the collection automator guide
    (C(docs/automator-guide.md)) for credential and scope guidance.
options:
  state:
    description: Desired host entry state.
    type: str
    choices: [present, absent]
    default: present
  server_url:
    description:
      - Auto-enrollment URL or PatchMon instance root (for example C(https://patchmon.example.com)).
      - Used for auto-enrollment when O(state=present).
      - Prefer C(PATCHMON_SERVER_URL). The collection derives C(/api/v1/auto-enrollment) from it.
      - C(PATCHMON_ENROLLMENT_URL) overrides that derived URL. Setting it directly is discouraged.
      - Falls back to O(api_url) when omitted.
    type: str
  enrollment_key:
    description:
      - Auto-enrollment token key (required for O(state=present)). This value is a secret.
    type: str
  enrollment_secret:
    description:
      - Auto-enrollment token secret (required for O(state=present)). This value is a secret.
    type: str
  friendly_name:
    description: Display name for the host (required for O(state=present)).
    type: str
  machine_id:
    description: Optional unique machine identifier for enrollment deduplication.
    type: str
  host_id:
    description:
      - PatchMon host UUID.
      - Required for O(state=absent).
      - Optional for O(state=present) to re-key a never-reported host.
    type: str
  metadata:
    description: Optional metadata object passed to enrollment.
    type: dict
  force_enroll:
    description:
      - When true, always call enroll even if the host already appears in the Integration list.
      - Default is to skip enrollment when a matching host is found (requires Integration C(host:get)).
    type: bool
    default: false
  api_url:
    description:
      - Integration API hosts URL or instance root.
      - Required for O(state=absent) and for present-state existence checks.
      - Prefer C(PATCHMON_SERVER_URL). The collection derives C(/api/v1/api/hosts) from it.
      - C(PATCHMON_API_URL) overrides that derived URL. Setting it directly is discouraged.
    type: str
  api_key:
    description:
      - Integration API token key (Basic Auth username). This value is a secret.
    type: str
  api_secret:
    description:
      - Integration API token secret (Basic Auth password). This value is a secret.
    type: str
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
- name: Enroll a new host via auto-enrollment
  patchmon.core.host:
    state: present
    server_url: "{{ lookup('patchmon.core.endpoint', 'enrollment') }}"
    enrollment_key: "{{ lookup('env', 'PATCHMON_ENROLLMENT_KEY') }}"
    enrollment_secret: "{{ lookup('env', 'PATCHMON_ENROLLMENT_SECRET') }}"
    friendly_name: "{{ inventory_hostname }}"
    machine_id: "{{ ansible_machine_id | default(omit) }}"
  delegate_to: localhost
  register: pm_host

- name: Delete a host (requires host:delete)
  patchmon.core.host:
    state: absent
    api_url: "{{ lookup('patchmon.core.endpoint', 'api') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
  delegate_to: localhost
"""

RETURN = r"""
host:
  description: Host object from enroll or prior Integration list match.
  returned: success
  type: dict
changed:
  description: Whether the host was created, re-enrolled, or deleted.
  type: bool
reenrolled:
  description: True when enrollment re-issued credentials for an existing host.
  returned: when applicable
  type: bool
already_exists:
  description: True when present-state skipped enroll because the host was listed.
  returned: when applicable
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonClient,
    PatchMonEnrollmentClient,
)

_MACHINE_ID_MATCH_FEEDBACK = (
    "Enrollment returned 409 machine_id_match without host_id. "
    "patchmon.core.host stopped.\n"
    "\n"
    "Create a PatchMon feedback request: https://feedback.patchmon.net/\n"
    "\n"
    "Subject: Return host_id on enrollment machine_id_match\n"
    "\n"
    "Description:\n"
    "POST /api/v1/auto-enrollment/enroll returns 409 machine_id_match with "
    "friendly_name and without host_id. The other 409 codes include host_id.\n"
    "\n"
    "Please include host_id on machine_id_match as well."
)


def _integration_client(module):
    api_url = module.params.get("api_url") or module.params.get("server_url")
    api_key = module.params.get("api_key")
    api_secret = module.params.get("api_secret")
    if not api_url or not api_key or not api_secret:
        return None
    return PatchMonClient(
        api_url=api_url,
        api_key=api_key,
        api_secret=api_secret,
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )


def _ensure_present(module):
    friendly_name = module.params.get("friendly_name")
    if not friendly_name:
        module.fail_json(msg="friendly_name is required when state=present")
    has_enrollment = bool(
        module.params.get("enrollment_key") and module.params.get("enrollment_secret")
    )
    if not has_enrollment:
        module.fail_json(
            msg="enrollment_key and enrollment_secret are required when state=present"
        )

    server_url = module.params.get("server_url") or module.params.get("api_url")
    if not server_url:
        module.fail_json(msg="server_url or api_url is required when state=present")

    existing = None
    integration = _integration_client(module)
    if integration is not None and not module.params["force_enroll"]:
        try:
            existing = integration.find_host(
                host_id=module.params.get("host_id"),
                friendly_name=friendly_name,
            )
        except PatchMonAPIError as exc:
            # Missing host:get should not block enrollment.
            if exc.status_code not in (401, 403):
                module.fail_json(msg=str(exc))
            existing = None

    if existing is not None:
        module.exit_json(
            changed=False,
            already_exists=True,
            host=existing,
            msg="Host already present in PatchMon Integration inventory",
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            host={"friendly_name": friendly_name},
            msg="Would enroll host via auto-enrollment API",
        )

    client = PatchMonEnrollmentClient(
        server_url=server_url,
        enrollment_key=module.params["enrollment_key"],
        enrollment_secret=module.params["enrollment_secret"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )

    try:
        payload = client.enroll(
            friendly_name=friendly_name,
            machine_id=module.params.get("machine_id"),
            host_id=module.params.get("host_id"),
            metadata=module.params.get("metadata"),
        )
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    # 409 conflict payloads are returned without raising (ok_statuses).
    if isinstance(payload, dict) and payload.get("error"):
        code = payload.get("code")
        if code in ("machine_id_match", "host_reporting"):
            if code == "machine_id_match" and not payload.get("host_id"):
                extra = {
                    key: value for key, value in payload.items() if key != "msg"
                }
                module.fail_json(msg=_MACHINE_ID_MATCH_FEEDBACK, **extra)
            module.exit_json(
                changed=False,
                already_exists=True,
                host={
                    "id": payload.get("host_id"),
                    "friendly_name": payload.get("friendly_name") or friendly_name,
                },
                msg=payload.get("error"),
                conflict_code=code,
            )
        module.fail_json(msg=payload.get("error") or "enrollment conflict", **payload)

    host = payload.get("host") if isinstance(payload, dict) else None
    reenrolled = bool(isinstance(payload, dict) and payload.get("reenrolled"))
    enroll_msg = (payload or {}).get("message") if isinstance(payload, dict) else None
    module.exit_json(
        changed=True,
        host=host or {},
        reenrolled=reenrolled,
        msg=enroll_msg,
    )


def _ensure_absent(module):
    host_id = module.params.get("host_id")
    if not host_id:
        module.fail_json(msg="host_id is required when state=absent")
    for key in ("api_url", "api_key", "api_secret"):
        if not module.params.get(key):
            module.fail_json(
                msg="{0} is required when state=absent (Integration API host:delete)".format(
                    key
                )
            )

    client = PatchMonClient(
        api_url=module.params["api_url"],
        api_key=module.params["api_key"],
        api_secret=module.params["api_secret"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )

    existing = None
    try:
        existing = client.find_host(host_id=host_id)
    except PatchMonAPIError as exc:
        if exc.status_code not in (401, 403):
            # Proceed to delete even if list failed for other reasons.
            pass
        else:
            # Still allow delete attempt when list is forbidden.
            existing = None

    if existing is None and not module.params.get("force_enroll"):
        # Try delete anyway — 404 means already gone.
        pass

    if module.check_mode:
        module.exit_json(
            changed=True,
            host={"id": host_id},
            msg="Would delete host via Integration API",
        )

    try:
        result = client.delete_host(host_id)
    except PatchMonAPIError as exc:
        if exc.status_code == 404:
            module.exit_json(
                changed=False, host={"id": host_id}, msg="Host already absent"
            )
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    module.exit_json(
        changed=True,
        host={"id": host_id},
        result=result,
        msg="Host deleted",
    )


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", default="present", choices=["present", "absent"]),
            server_url=dict(type="str"),
            enrollment_key=dict(type="str", no_log=True),
            enrollment_secret=dict(type="str", no_log=True),
            friendly_name=dict(type="str"),
            machine_id=dict(type="str"),
            host_id=dict(type="str"),
            metadata=dict(type="dict"),
            force_enroll=dict(type="bool", default=False),
            api_url=dict(type="str"),
            api_key=dict(type="str", no_log=True),
            api_secret=dict(type="str", no_log=True),
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

    if module.params["state"] == "present":
        _ensure_present(module)
    else:
        _ensure_absent(module)


def main():
    run_module()


if __name__ == "__main__":
    main()

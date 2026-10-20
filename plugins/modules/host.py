#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host
short_description: Create, update, or delete a PatchMon host entry
version_added: "2.0.0"
description:
  - Ensures a PatchMon host entry is present (auto-enrollment) or absent (Integration API delete).
  - C(state=present) uses the Auto-Enrollment API
    (C(X-Auto-Enrollment-Key) / C(X-Auto-Enrollment-Secret)), not Integration Basic Auth.
  - C(state=absent) uses the Integration API and requires scope C(host:delete).
  - Optional desired-state fields update an existing host and are ignored when omitted.
    Scalar fields need C(host:patch). Group membership needs C(host:put). Compares need C(host:get).
  - C(state=absent) ignores desired-state fields.
  - See U(https://patchmon.net/docs/patchmon-api-integrations-guide) and the collection
    C(docs/permissions.md) for credential and scope guidance.
options:
  state:
    description: Desired host entry state.
    type: str
    choices: [present, absent]
    default: present
  server_url:
    description:
      - PatchMon instance root (for example C(https://patchmon.example.com)).
      - Used for auto-enrollment when O(state=present).
      - Falls back to O(api_url) when omitted.
    type: str
  enrollment_key:
    description: Auto-enrollment token key (required for O(state=present)).
    type: str
    no_log: true
  enrollment_secret:
    description: Auto-enrollment token secret (required for O(state=present)).
    type: str
    no_log: true
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
  friendly_name_update:
    description:
      - Desired friendly name for an existing host.
      - Omitted means the current name is left unchanged. This is separate from O(friendly_name),
        which is only the enrollment display name.
      - Requires Integration scopes C(host:get) and C(host:patch).
    type: str
  notes:
    description:
      - Desired host notes. An empty string clears notes.
      - Omitted means notes are left unchanged.
      - Requires Integration scopes C(host:get) and C(host:patch).
    type: str
  auto_update:
    description:
      - Desired agent auto-update flag.
      - Omitted means the current flag is left unchanged. V(false) disables auto-update.
      - Requires Integration scopes C(host:get) and C(host:patch).
    type: raw
  host_down_alerts:
    description:
      - Desired host-down alert override.
      - Omitted means the current setting is left unchanged, including inherit-from-global.
      - V(true) or V(false) sets an explicit override. This module does not clear the override
        back to inherit.
      - Requires Integration scopes C(host:get) and C(host:patch).
    type: raw
  groups:
    description:
      - Desired host group membership, as group names or UUIDs.
      - Replaces the full membership set. An empty list removes every group.
      - Omitted means membership is left unchanged.
      - Names are resolved with C(GET /api/v1/api/host-groups).
      - Requires Integration scopes C(host:get) and C(host:put).
    type: list
    elements: str
  api_url:
    description:
      - Integration API hosts URL or instance root.
      - Required for O(state=absent) and for present-state existence checks.
    type: str
  api_key:
    description: Integration API token key (Basic Auth username).
    type: str
    no_log: true
  api_secret:
    description: Integration API token secret (Basic Auth password).
    type: str
    no_log: true
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
    server_url: https://patchmon.example.com
    enrollment_key: "{{ lookup('env', 'PATCHMON_ENROLLMENT_KEY') }}"
    enrollment_secret: "{{ lookup('env', 'PATCHMON_ENROLLMENT_SECRET') }}"
    friendly_name: "{{ inventory_hostname }}"
    machine_id: "{{ ansible_machine_id | default(omit) }}"
  delegate_to: localhost
  register: pm_host

- name: Delete a host (requires host:delete)
  patchmon.core.host:
    state: absent
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
  delegate_to: localhost

- name: Set notes and group membership on an existing host
  patchmon.core.host:
    state: present
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    notes: "Owned by the platform team"
    groups:
      - Automated
      - No_Reboot
  delegate_to: localhost
"""

RETURN = r"""
host:
  description: Host object from enroll or prior Integration list match.
  returned: success
  type: dict
changed:
  description: Whether the host was created, re-enrolled, updated, or deleted.
  type: bool
diff:
  description: Before and after values for managed fields that drifted.
  returned: when a managed field changed, including check mode
  type: dict
updates:
  description: Managed field names that were written, or would be written in check mode.
  returned: when managed fields are set
  type: list
  elements: str
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


def _coerce_bool(value, label):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("true", "yes", "on", "1"):
            return True
        if token in ("false", "no", "off", "0"):
            return False
    raise ValueError("{0} must be a boolean (got {1!r})".format(label, value))


def _managed_spec(params):
    """Map module params to reconcile_host kwargs. Omitted params stay unmanaged."""
    spec = {}
    if params.get("friendly_name_update") is not None:
        name = params["friendly_name_update"]
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("friendly_name_update must be 1-100 characters when set")
        spec["friendly_name"] = name
    if params.get("notes") is not None:
        spec["notes"] = params["notes"]
    if params.get("auto_update") is not None:
        spec["auto_update"] = _coerce_bool(params["auto_update"], "auto_update")
    if params.get("host_down_alerts") is not None:
        spec["host_down_alerts"] = _coerce_bool(
            params["host_down_alerts"], "host_down_alerts"
        )
    if params.get("groups") is not None:
        groups = params["groups"]
        if not isinstance(groups, list):
            raise ValueError("groups must be a list of group names or UUIDs")
        spec["groups"] = groups
    return spec


def _require_integration(module):
    client = _integration_client(module)
    if client is None:
        module.fail_json(
            msg=(
                "api_url, api_key, and api_secret are required to manage host "
                "fields (Integration scopes host:get plus host:patch and/or host:put)"
            )
        )
    return client


def _host_id_from_payload(payload, fallback=None):
    if isinstance(payload, dict):
        host = payload.get("host")
        if isinstance(host, dict) and host.get("id"):
            return host.get("id")
        if payload.get("host_id"):
            return payload.get("host_id")
        if payload.get("id"):
            return payload.get("id")
    return fallback


def _finish_managed(
    module,
    client,
    host_id,
    managed,
    host,
    enrolled_changed,
    already,
    reenrolled,
    msg=None,
):
    if not host_id:
        module.fail_json(
            msg="A host id is required before managed fields can be applied"
        )
    try:
        reconciled = client.reconcile_host(
            host_id, check_mode=module.check_mode, **managed
        )
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    result_host = dict(host) if isinstance(host, dict) else {}
    result_host.setdefault("id", host_id)
    result = {
        "changed": bool(enrolled_changed or reconciled["changed"]),
        "host": result_host,
        "already_exists": already,
        "reenrolled": reenrolled,
        "updates": reconciled["updates"],
    }
    if msg:
        result["msg"] = msg
    if reconciled["changed"]:
        result["diff"] = reconciled["diff"]
    module.exit_json(**result)


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
    try:
        managed = _managed_spec(module.params)
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    has_enrollment = bool(
        module.params.get("enrollment_key") and module.params.get("enrollment_secret")
    )
    if managed and not has_enrollment:
        host_id = module.params.get("host_id")
        if not host_id:
            module.fail_json(
                msg=(
                    "host_id is required to update a host without enrollment "
                    "credentials"
                )
            )
        client = _require_integration(module)
        _finish_managed(
            module,
            client,
            host_id,
            managed,
            host={"id": host_id},
            enrolled_changed=False,
            already=True,
            reenrolled=False,
        )

    friendly_name = module.params.get("friendly_name")
    if not friendly_name:
        module.fail_json(msg="friendly_name is required when state=present")
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
            # Missing host:get should not block enrollment; warn via msg on result.
            if exc.status_code not in (401, 403):
                module.fail_json(msg=str(exc))
            existing = None

    if existing is not None and not managed:
        module.exit_json(
            changed=False,
            already_exists=True,
            host=existing,
            msg="Host already present in PatchMon Integration inventory",
        )

    if existing is not None:
        host_id = existing.get("id") or module.params.get("host_id")
        client = _require_integration(module)
        _finish_managed(
            module,
            client,
            host_id,
            managed,
            host=existing,
            enrolled_changed=False,
            already=True,
            reenrolled=False,
            msg="Host already present in PatchMon Integration inventory",
        )

    if module.check_mode:
        result = {
            "changed": True,
            "host": {"friendly_name": friendly_name},
            "msg": "Would enroll host via auto-enrollment API",
        }
        if managed:
            result["diff"] = {"before": {}, "after": managed}
            result["updates"] = sorted(managed.keys())
        module.exit_json(**result)

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
            conflict_host = {
                "id": payload.get("host_id"),
                "friendly_name": payload.get("friendly_name") or friendly_name,
            }
            if not managed:
                module.exit_json(
                    changed=False,
                    already_exists=True,
                    host=conflict_host,
                    msg=payload.get("error"),
                    conflict_code=code,
                )
            integration = _require_integration(module)
            _finish_managed(
                module,
                integration,
                conflict_host.get("id"),
                managed,
                host=conflict_host,
                enrolled_changed=False,
                already=True,
                reenrolled=False,
                msg=payload.get("error"),
            )
        module.fail_json(msg=payload.get("error") or "enrollment conflict", **payload)

    host = payload.get("host") if isinstance(payload, dict) else None
    reenrolled = bool(isinstance(payload, dict) and payload.get("reenrolled"))
    enroll_msg = (payload or {}).get("message") if isinstance(payload, dict) else None
    if not managed:
        module.exit_json(
            changed=True,
            host=host or {},
            reenrolled=reenrolled,
            msg=enroll_msg,
        )

    integration = _require_integration(module)
    _finish_managed(
        module,
        integration,
        _host_id_from_payload(payload, module.params.get("host_id")),
        managed,
        host=host or {},
        enrolled_changed=True,
        already=False,
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
            friendly_name_update=dict(type="str"),
            notes=dict(type="str"),
            auto_update=dict(type="raw"),
            host_down_alerts=dict(type="raw"),
            groups=dict(type="list", elements="str"),
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

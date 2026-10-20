#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: host_action
short_description: Run a non-idempotent PatchMon host command
version_added: "2.0.0"
description:
  - Queues a package report, forces an agent update, or regenerates per-host agent credentials.
  - These calls are commands. A successful run is always C(changed=true).
  - Requires Integration API scope C(host:update). This scope is separate from C(host:patch),
    C(host:put), and C(host:delete).
  - C(regenerate_credentials) returns a one-time agent key and invalidates the previous key.
    Set C(no_log=true) on the task so the key is not written to logs. Register the result
    if you need to store the key.
extends_documentation_fragment:
  - patchmon.core.auth
options:
  host_id:
    description: PatchMon host UUID.
    type: str
    required: true
  action:
    description: Command to run.
    type: str
    required: true
    choices: [fetch_report, force_agent_update, regenerate_credentials]
author:
  - mrjoshuap
requirements:
  - requests >= 2.25.1
"""

EXAMPLES = r"""
- name: Queue a package report without SSH
  patchmon.core.host_action:
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    action: fetch_report
  delegate_to: localhost

- name: Regenerate agent credentials
  patchmon.core.host_action:
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    action: regenerate_credentials
  delegate_to: localhost
  register: pm_agent_creds
  no_log: true
"""

RETURN = r"""
changed:
  description: True when the command succeeded, or would be sent in check mode.
  type: bool
action:
  description: Command that ran.
  returned: success
  type: str
host_id:
  description: Host UUID the command targeted.
  returned: success
  type: str
job_id:
  description: Queue job id when the API returns one.
  returned: when the API includes a job id
  type: str
api_id:
  description: New per-host agent API id. Returned once.
  returned: when O(action=regenerate_credentials) and check mode is off
  type: str
api_key:
  description:
    - New per-host agent API key. Returned once. The previous key no longer works.
    - Run the task with C(no_log=true).
  returned: when O(action=regenerate_credentials) and check mode is off
  type: str
warning:
  description: Warning text from the API, when present.
  returned: when the API includes a warning
  type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    HAS_REQUESTS,
    REQUESTS_IMPORT_ERROR,
    PatchMonAPIError,
    PatchMonClient,
)


_CHECK_MODE_MSG = {
    "fetch_report": "Would queue a package report",
    "force_agent_update": "Would queue a forced agent update",
    "regenerate_credentials": (
        "Would regenerate agent credentials and invalidate the previous key"
    ),
}


def _field(payload, *names):
    if not isinstance(payload, dict):
        return None
    for name in names:
        if payload.get(name):
            return payload.get(name)
    return None


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type="str", required=True),
            api_key=dict(type="str", required=True, no_log=True),
            api_secret=dict(type="str", required=True, no_log=True),
            verify_ssl=dict(type="bool", default=True),
            timeout=dict(type="int", default=30),
            host_id=dict(type="str", required=True),
            action=dict(
                type="str",
                required=True,
                choices=[
                    "fetch_report",
                    "force_agent_update",
                    "regenerate_credentials",
                ],
            ),
        ),
        supports_check_mode=True,
    )

    if not HAS_REQUESTS:
        module.fail_json(
            msg="The Python requests library is required",
            exception=str(REQUESTS_IMPORT_ERROR),
        )

    host_id = module.params["host_id"]
    action = module.params["action"]
    if module.check_mode:
        module.exit_json(
            changed=True,
            host_id=host_id,
            action=action,
            msg=_CHECK_MODE_MSG[action],
        )

    client = PatchMonClient(
        api_url=module.params["api_url"],
        api_key=module.params["api_key"],
        api_secret=module.params["api_secret"],
        verify_ssl=module.params["verify_ssl"],
        timeout=module.params["timeout"],
    )
    try:
        payload = getattr(client, action)(host_id)
    except PatchMonAPIError as exc:
        module.fail_json(msg=str(exc), status_code=exc.status_code)

    result = {
        "changed": True,
        "host_id": host_id,
        "action": action,
    }
    message = _field(payload, "message")
    if message:
        result["msg"] = message
    job_id = _field(payload, "job_id", "jobId")
    if job_id:
        result["job_id"] = job_id
    warning = _field(payload, "warning")
    if warning:
        result["warning"] = warning

    if action == "regenerate_credentials":
        api_id = _field(payload, "api_id", "apiId")
        api_key = _field(payload, "api_key", "apiKey")
        if api_id:
            result["api_id"] = api_id
        if api_key:
            result["api_key"] = api_key
        result["msg"] = (
            "Agent credentials regenerated. The previous key is invalid. "
            "Set no_log=true on this task."
        )

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lookup plugin that resolves PatchMon enrollment and Integration URLs."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: endpoint
short_description: Resolve PatchMon enrollment and Integration API URLs
version_added: "2.0.4"
description:
  - Resolves a PatchMon URL from the environment.
  - Prefer C(PATCHMON_SERVER_URL). This lookup derives the auto-enrollment URL
    and the Integration hosts URL from that instance root.
  - C(PATCHMON_ENROLLMENT_URL) overrides the derived enrollment URL.
  - C(PATCHMON_API_URL) overrides the derived hosts URL, and is also a last
    resort for enrollment when C(PATCHMON_SERVER_URL) is unset.
  - Setting C(PATCHMON_ENROLLMENT_URL) or C(PATCHMON_API_URL) directly is discouraged.
options:
  _terms:
    description:
      - Which URL to resolve.
      - C(api) is the Integration hosts endpoint (C(/api/v1/api/hosts)).
      - C(enrollment) is the auto-enrollment base URL (C(/api/v1/auto-enrollment)).
    required: true
    type: str
    choices: [api, enrollment]
author:
  - mrjoshuap
"""

EXAMPLES = r"""
- name: Use the hosts URL derived from PATCHMON_SERVER_URL
  ansible.builtin.debug:
    msg: "{{ lookup('patchmon.core.endpoint', 'api') }}"

- name: Use the enrollment URL derived from PATCHMON_SERVER_URL
  ansible.builtin.debug:
    msg: "{{ lookup('patchmon.core.endpoint', 'enrollment') }}"
"""

RETURN = r"""
_raw:
  description:
    - The resolved URL, or an empty string when no PatchMon URL environment variable is set.
  type: list
  elements: str
"""

from ansible.errors import AnsibleOptionsError
from ansible.plugins.lookup import LookupBase

from ansible_collections.patchmon.core.plugins.module_utils.patchmon_api import (
    resolve_api_url,
    resolve_enrollment_url,
)


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if not terms:
            raise AnsibleOptionsError("endpoint kind is required: api or enrollment")

        resolvers = {
            "api": resolve_api_url,
            "enrollment": resolve_enrollment_url,
        }
        results = []
        for term in terms:
            kind = str(term).strip().lower()
            resolver = resolvers.get(kind)
            if resolver is None:
                raise AnsibleOptionsError(
                    "endpoint kind must be 'api' or 'enrollment', not {0}".format(term)
                )
            results.append(resolver())
        return results

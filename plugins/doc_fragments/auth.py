# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared PatchMon Integration API connection options for modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    """Documentation fragment for PatchMon API authentication options."""

    DOCUMENTATION = r"""
options:
  api_url:
    description:
      - PatchMon hosts endpoint or instance root.
      - Canonical form is C(https://patchmon.example.com/api/v1/api/hosts).
      - Instance root is accepted; the collection appends C(/api/v1/api/hosts) when needed.
      - These options authenticate to the Integration API (HTTP Basic), not Auto-Enrollment.
      - Typical minimum scope is C(host:get). Destructive modules require C(host:delete).
      - See the collection C(docs/permissions.md) for the full scope matrix.
      - Environment variable C(PATCHMON_API_URL). Ini section C(patchmon), key C(api_url).
    required: true
    type: str
  api_key:
    description:
      - PatchMon Integration API Token Key (Basic Auth username). This value is a secret.
      - Prefer environment variables, Vault, or Controller credentials over plaintext YAML.
      - Environment variable C(PATCHMON_API_KEY). Ini section C(patchmon), key C(api_key).
    required: true
    type: str
  api_secret:
    description:
      - PatchMon Integration API Token Secret (Basic Auth password). This value is a secret.
      - Prefer environment variables, Vault, or Controller credentials over plaintext YAML.
      - Environment variable C(PATCHMON_API_SECRET). Ini section C(patchmon), key C(api_secret).
    required: true
    type: str
  verify_ssl:
    description:
      - Verify the PatchMon TLS certificate.
      - Set to false only in lab environments.
      - Environment variable C(PATCHMON_VERIFY_SSL). Ini section C(patchmon), key C(verify_ssl).
    type: bool
    default: true
  timeout:
    description: HTTP timeout in seconds for PatchMon API requests.
    type: int
    default: 30
"""

# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared PatchMon Integration API connection options for plugins."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    """Documentation fragment for plugin configuration of PatchMon API auth."""

    DOCUMENTATION = r"""
options:
  api_url:
    description:
      - PatchMon hosts endpoint or instance root.
      - Prefer C(PATCHMON_SERVER_URL). The collection derives C(https://patchmon.example.com/api/v1/api/hosts) from that instance root.
      - C(PATCHMON_API_URL) overrides the derived hosts URL. Setting it directly is discouraged.
      - Instance root is accepted; the collection appends C(/api/v1/api/hosts) when needed.
      - These options authenticate to the Integration API (HTTP Basic), not Auto-Enrollment.
      - Typical minimum scope is C(host:get).
      - See the Credentials chapter of the collection automator guide
        (C(docs/automator-guide.md)) for the full scope matrix.
    required: true
    type: str
    env:
      - name: PATCHMON_API_URL
      - name: PATCHMON_SERVER_URL
    ini:
      - section: patchmon
        key: api_url
  api_key:
    description:
      - PatchMon Integration API Token Key (Basic Auth username). This value is a secret.
      - Prefer environment variables, Vault, or Controller credentials over plaintext YAML.
    required: true
    type: str
    env:
      - name: PATCHMON_API_KEY
    ini:
      - section: patchmon
        key: api_key
  api_secret:
    description:
      - PatchMon Integration API Token Secret (Basic Auth password). This value is a secret.
      - Prefer environment variables, Vault, or Controller credentials over plaintext YAML.
    required: true
    type: str
    env:
      - name: PATCHMON_API_SECRET
    ini:
      - section: patchmon
        key: api_secret
  verify_ssl:
    description:
      - Verify the PatchMon TLS certificate.
      - Set to false only in lab environments.
    type: bool
    default: true
    env:
      - name: PATCHMON_VERIFY_SSL
    ini:
      - section: patchmon
        key: verify_ssl
  timeout:
    description: HTTP timeout in seconds for PatchMon API requests.
    type: int
    default: 30
"""

# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared PatchMon Integration API connection options."""

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
    required: true
    type: str
    env:
      - name: PATCHMON_API_URL
    ini:
      - section: patchmon
        key: api_url
  api_key:
    description: PatchMon API Token Key (Basic Auth username).
    required: true
    type: str
    no_log: true
    env:
      - name: PATCHMON_API_KEY
    ini:
      - section: patchmon
        key: api_key
  api_secret:
    description: PatchMon API Token Secret (Basic Auth password).
    required: true
    type: str
    no_log: true
    env:
      - name: PATCHMON_API_SECRET
    ini:
      - section: patchmon
        key: api_secret
  verify_ssl:
    description: Verify the PatchMon TLS certificate.
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

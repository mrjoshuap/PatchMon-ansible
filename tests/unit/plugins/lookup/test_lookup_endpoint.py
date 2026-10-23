# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the endpoint lookup plugin."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from ansible.errors import AnsibleOptionsError

from ansible_collections.patchmon.core.plugins.lookup import (
    endpoint as lookup_mod,
)


class FakeLookup(lookup_mod.LookupModule):
    def __init__(self):
        return None


def test_lookup_requires_terms():
    plugin = FakeLookup()
    with pytest.raises(AnsibleOptionsError):
        plugin.run([])


def test_lookup_rejects_unknown_kind():
    plugin = FakeLookup()
    with pytest.raises(AnsibleOptionsError):
        plugin.run(["hosts"])


def test_lookup_resolves_api_and_enrollment(monkeypatch):
    monkeypatch.delenv("PATCHMON_API_URL", raising=False)
    monkeypatch.delenv("PATCHMON_ENROLLMENT_URL", raising=False)
    monkeypatch.setenv("PATCHMON_SERVER_URL", "https://patchmon.example.com")
    plugin = FakeLookup()
    assert plugin.run(["api", "enrollment"]) == [
        "https://patchmon.example.com/api/v1/api/hosts",
        "https://patchmon.example.com/api/v1/auto-enrollment",
    ]

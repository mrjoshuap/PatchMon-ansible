# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the host lookup plugin."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from ansible.errors import AnsibleOptionsError

from ansible_collections.patchmon.ansible.plugins.lookup import (
    host as lookup_mod,
)


class FakeLookup(lookup_mod.LookupModule):
    def __init__(self, options=None):
        self._options = options or {
            "api_url": "https://patchmon.example.com",
            "api_key": "key",
            "api_secret": "secret",
            "verify_ssl": True,
            "timeout": 30,
            "resource": "system",
            "updates_only": False,
        }

    def set_options(self, var_options=None, direct=None):
        if direct:
            self._options.update(direct)

    def get_option(self, option):
        return self._options[option]


def test_lookup_requires_terms():
    plugin = FakeLookup()
    with pytest.raises(AnsibleOptionsError):
        plugin.run([], variables={})


class _StubClient(object):
    """Satisfies fetcher map construction; override methods under test."""

    def __init__(self, *args, **kwargs):
        pass

    def get_host_info(self, host_id):
        raise AssertionError("info should not be called")

    def get_host_stats(self, host_id):
        raise AssertionError("stats should not be called")

    def get_host_system(self, host_id):
        raise AssertionError("system should not be called")

    def get_host_network(self, host_id):
        raise AssertionError("network should not be called")

    def get_host_integrations(self, host_id):
        raise AssertionError("integrations should not be called")

    def get_host_notes(self, host_id):
        raise AssertionError("notes should not be called")

    def get_host_packages(self, host_id, updates_only=False):
        raise AssertionError("packages should not be called")


def test_lookup_fetches_system(monkeypatch):
    calls = []

    class FakeClient(_StubClient):
        def get_host_system(self, host_id):
            calls.append(host_id)
            return {"needs_reboot": True, "kernel_version": "6.8.0"}

    monkeypatch.setattr(lookup_mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(lookup_mod, "HAS_REQUESTS", True)

    plugin = FakeLookup()
    results = plugin.run(["host-1"], variables={})

    assert calls == ["host-1"]
    assert results == [{"needs_reboot": True, "kernel_version": "6.8.0"}]


def test_lookup_packages_updates_only(monkeypatch):
    class FakeClient(_StubClient):
        def get_host_packages(self, host_id, updates_only=False):
            assert updates_only is True
            return {"packages": [{"name": "openssl"}]}

    monkeypatch.setattr(lookup_mod, "PatchMonClient", FakeClient)
    monkeypatch.setattr(lookup_mod, "HAS_REQUESTS", True)

    plugin = FakeLookup(
        options={
            "api_url": "https://patchmon.example.com",
            "api_key": "key",
            "api_secret": "secret",
            "verify_ssl": True,
            "timeout": 30,
            "resource": "packages",
            "updates_only": True,
        }
    )
    results = plugin.run(["host-2"], variables={})
    assert results[0]["packages"][0]["name"] == "openssl"

# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for PatchMon API helpers."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.ansible.plugins.module_utils import (
    patchmon_api as api,
)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "https://patchmon.example.com/api/v1/api/hosts",
            "https://patchmon.example.com/api/v1/api/hosts",
        ),
        (
            "https://patchmon.example.com/api/v1/api/hosts/",
            "https://patchmon.example.com/api/v1/api/hosts",
        ),
        (
            "https://patchmon.example.com",
            "https://patchmon.example.com/api/v1/api/hosts",
        ),
        (
            "https://patchmon.example.com/",
            "https://patchmon.example.com/api/v1/api/hosts",
        ),
        (
            "https://patchmon.example.com/api/v1/api",
            "https://patchmon.example.com/api/v1/api/hosts",
        ),
    ],
)
def test_normalize_hosts_url(given, expected):
    assert api.normalize_hosts_url(given) == expected


def test_build_hosts_url_with_stats_and_hostgroup():
    url = api.build_hosts_url(
        "https://patchmon.example.com/api/v1/api/hosts",
        include_stats=True,
        hostgroup=["Production", "Development"],
    )
    assert url.startswith("https://patchmon.example.com/api/v1/api/hosts?")
    assert "include=stats" in url
    assert "hostgroup=Production%2CDevelopment" in url or "hostgroup=Production,Development" in url


def test_host_resource_url_packages_updates_only():
    url = api.host_resource_url(
        "https://patchmon.example.com/api/v1/api/hosts",
        "abc-123",
        "packages",
        query={"updates_only": "true"},
    )
    assert url == (
        "https://patchmon.example.com/api/v1/api/hosts/abc-123/packages"
        "?updates_only=true"
    )


def test_client_requires_credentials():
    with pytest.raises(api.PatchMonAPIError):
        api.PatchMonClient("https://patchmon.example.com", "", "secret")


def test_get_hosts_success(monkeypatch):
    class FakeResponse(object):
        status_code = 200
        content = b'{"hosts":[]}'
        is_redirect = False
        headers = {"Content-Type": "application/json"}

        def json(self):
            return {"hosts": [{"hostname": "a.example.com", "ip": "1.2.3.4"}]}

    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            assert method == "GET"
            assert "include=stats" in url
            return FakeResponse()

    monkeypatch.setattr(api.requests, "Session", FakeSession)

    client = api.PatchMonClient(
        "https://patchmon.example.com/api/v1/api/hosts",
        "key",
        "secret",
    )
    payload = client.get_hosts(include_stats=True)
    assert payload["hosts"][0]["hostname"] == "a.example.com"


def test_get_hosts_http_error(monkeypatch):
    class FakeResponse(object):
        status_code = 403
        content = b'{"error":"Access denied"}'
        is_redirect = False
        text = '{"error":"Access denied"}'
        headers = {"Content-Type": "application/json"}

        def json(self):
            return {"error": "Access denied"}

    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(api.requests, "Session", FakeSession)
    client = api.PatchMonClient(
        "https://patchmon.example.com/api/v1/api/hosts",
        "key",
        "secret",
    )
    with pytest.raises(api.PatchMonAPIError) as exc:
        client.get_hosts()
    assert exc.value.status_code == 403
    assert "Access denied" in str(exc.value)

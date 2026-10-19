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


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("https://patchmon.example.com", "https://patchmon.example.com"),
        ("https://patchmon.example.com/", "https://patchmon.example.com"),
        (
            "https://patchmon.example.com/api/v1/api/hosts",
            "https://patchmon.example.com",
        ),
        (
            "https://patchmon.example.com/api/v1/api",
            "https://patchmon.example.com",
        ),
    ],
)
def test_normalize_instance_url(given, expected):
    assert api.normalize_instance_url(given) == expected


def test_delete_host(monkeypatch):
    class FakeResponse(object):
        status_code = 200
        content = b'{"message":"Host deleted successfully"}'
        is_redirect = False
        headers = {"Content-Type": "application/json"}
        text = content.decode()

        def json(self):
            return {"message": "Host deleted successfully"}

    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            assert method == "DELETE"
            assert url.endswith("/abc-123")
            return FakeResponse()

    client = api.PatchMonClient(
        "https://patchmon.example.com", "key", "secret"
    )
    monkeypatch.setattr(client, "_session", FakeSession())
    result = client.delete_host("abc-123")
    assert result["message"] == "Host deleted successfully"


def test_enrollment_enroll(monkeypatch):
    class FakeResponse(object):
        status_code = 201
        content = b'{"message":"ok","host":{"id":"1"}}'
        is_redirect = False
        headers = {"Content-Type": "application/json"}
        text = content.decode()

        def json(self):
            return {"message": "ok", "host": {"id": "1"}}

    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            assert method == "POST"
            assert url.endswith("/api/v1/auto-enrollment/enroll")
            assert kwargs["headers"]["X-Auto-Enrollment-Key"] == "ek"
            return FakeResponse()

    client = api.PatchMonEnrollmentClient(
        "https://patchmon.example.com", "ek", "es"
    )
    monkeypatch.setattr(client, "_session", FakeSession())
    result = client.enroll(friendly_name="web1")
    assert result["host"]["id"] == "1"

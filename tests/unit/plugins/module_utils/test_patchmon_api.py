# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for PatchMon API helpers."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.core.plugins.module_utils import (
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


class _JsonResponse(object):
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload
        self.is_redirect = False
        self.headers = {"Content-Type": "application/json"}
        self.content = b"{}"
        self.text = "{}"

    def json(self):
        return self._payload


def _client_with_router(monkeypatch, router):
    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            return router(method, url, kwargs.get("json"))

    client = api.PatchMonClient(
        "https://patchmon.example.com/api/v1/api/hosts", "key", "secret"
    )
    monkeypatch.setattr(client, "_session", FakeSession())
    return client


def test_reconcile_skips_writes_when_values_match(monkeypatch):
    calls = []

    def router(method, url, body):
        calls.append((method, url, body))
        if url.endswith("/notes"):
            return _JsonResponse({"host_id": "h1", "notes": "same"})
        if url.endswith("/info"):
            return _JsonResponse(
                {
                    "friendly_name": "web1",
                    "auto_update": False,
                    "host_down_alerts_enabled": False,
                    "host_groups": [{"id": "g1", "name": "Automated"}],
                }
            )
        if url.endswith("/host-groups"):
            return _JsonResponse(
                {"host_groups": [{"id": "g1", "name": "Automated"}]}
            )
        raise AssertionError(url)

    client = _client_with_router(monkeypatch, router)
    result = client.reconcile_host(
        "h1",
        friendly_name="web1",
        notes="same",
        auto_update=False,
        host_down_alerts=False,
        groups=["Automated"],
    )
    assert result["changed"] is False
    assert result["updates"] == []
    assert all(call[0] == "GET" for call in calls)


def test_reconcile_patches_only_drift_and_skips_in_check_mode(monkeypatch):
    calls = []

    def router(method, url, body):
        calls.append((method, url, body))
        if url.endswith("/notes"):
            return _JsonResponse({"notes": "old"})
        raise AssertionError(url)

    client = _client_with_router(monkeypatch, router)
    result = client.reconcile_host("h1", notes="new", check_mode=True)
    assert result["changed"] is True
    assert result["updates"] == ["notes"]
    assert result["diff"]["before"]["notes"] == "old"
    assert result["diff"]["after"]["notes"] == "new"
    assert calls == [
        (
            "GET",
            "https://patchmon.example.com/api/v1/api/hosts/h1/notes",
            None,
        )
    ]

    calls[:] = []
    written = client.reconcile_host("h1", notes="new", check_mode=False)
    assert written["changed"] is True
    assert calls[1][0] == "PATCH"
    assert calls[1][2] == {"notes": "new"}


def test_reconcile_empty_groups_replaces_without_catalog_lookup(monkeypatch):
    calls = []

    def router(method, url, body):
        calls.append((method, url, body))
        if url.endswith("/info"):
            return _JsonResponse(
                {"host_groups": [{"id": "g1", "name": "Automated"}]}
            )
        if method == "PUT" and url.endswith("/groups"):
            return _JsonResponse({"message": "updated"})
        raise AssertionError((method, url))

    client = _client_with_router(monkeypatch, router)
    result = client.reconcile_host("h1", groups=[])
    assert result["changed"] is True
    assert result["updates"] == ["groups"]
    assert calls[0][0] == "GET"
    assert calls[1] == (
        "PUT",
        "https://patchmon.example.com/api/v1/api/hosts/h1/groups",
        {"groupIds": []},
    )
    assert not any("/host-groups" in call[1] for call in calls)


def test_reconcile_omitted_fields_do_not_call_the_api(monkeypatch):
    def router(method, url, body):
        raise AssertionError((method, url, body))

    client = _client_with_router(monkeypatch, router)
    result = client.reconcile_host("h1")
    assert result["changed"] is False
    assert result["updates"] == []


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


def test_enrollment_get_script_uses_params(monkeypatch):
    class FakeResponse(object):
        status_code = 200
        content = b"#!/bin/bash\necho ok\n"
        is_redirect = False
        headers = {"Content-Type": "text/plain"}
        text = content.decode()

        def json(self):
            raise ValueError("not json")

    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            assert method == "GET"
            assert url.endswith("/api/v1/auto-enrollment/script")
            assert "token_key" not in url
            assert "token_secret" not in url
            assert kwargs["params"]["type"] == "direct-host"
            assert kwargs["params"]["token_key"] == "ek"
            assert kwargs["params"]["token_secret"] == "es"
            assert kwargs["params"]["force"] == "true"
            return FakeResponse()

    client = api.PatchMonEnrollmentClient(
        "https://patchmon.example.com", "ek", "es"
    )
    monkeypatch.setattr(client, "_session", FakeSession())
    result = client.get_script(script_type="direct-host", force=True)
    assert result.startswith("#!/bin/bash")


def test_package_reports_and_agent_queue_limit(monkeypatch):
    seen = []

    class FakeResponse(object):
        status_code = 200
        content = b'{"ok": true}'
        is_redirect = False
        headers = {"Content-Type": "application/json"}
        text = content.decode()

        def json(self):
            return {"ok": True}

    class FakeSession(object):
        def __init__(self):
            self.headers = {}

        def request(self, method, url, **kwargs):
            seen.append((method, url))
            return FakeResponse()

    client = api.PatchMonClient(
        "https://patchmon.example.com/api/v1/api/hosts", "key", "secret"
    )
    monkeypatch.setattr(client, "_session", FakeSession())

    client.get_host_package_reports("abc-123", limit=5)
    client.get_host_agent_queue("abc-123", limit=5)

    assert seen[0] == (
        "GET",
        "https://patchmon.example.com/api/v1/api/hosts/abc-123/package_reports?limit=5",
    )
    assert seen[1] == (
        "GET",
        "https://patchmon.example.com/api/v1/api/hosts/abc-123/agent_queue?limit=5",
    )

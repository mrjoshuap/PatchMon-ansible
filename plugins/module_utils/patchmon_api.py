# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared PatchMon Integration API and Auto-Enrollment helpers."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from urllib.parse import urlencode, urlsplit, urlunsplit

try:
    import requests
    from requests.auth import HTTPBasicAuth

    HAS_REQUESTS = True
    REQUESTS_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - exercised when requests missing
    HAS_REQUESTS = False
    REQUESTS_IMPORT_ERROR = exc
    requests = None  # type: ignore[assignment]
    HTTPBasicAuth = None  # type: ignore[assignment]


HOSTS_PATH = "/api/v1/api/hosts"
AUTO_ENROLLMENT_PATH = "/api/v1/auto-enrollment"


class PatchMonAPIError(Exception):
    """Raised when a PatchMon API call fails."""

    def __init__(self, message, status_code=None, payload=None):
        super(PatchMonAPIError, self).__init__(message)
        self.status_code = status_code
        self.payload = payload


def normalize_instance_url(api_url):
    """Return the PatchMon instance root (scheme + netloc + optional base path).

    Accepts instance roots or Integration hosts URLs and strips
    ``/api/v1/api/hosts`` (and shorter ``/api/v1/api`` / ``/api/v1``) suffixes.
    """
    if not api_url:
        raise PatchMonAPIError("api_url is required")

    url = api_url.strip()
    parts = urlsplit(url)
    path = (parts.path or "").rstrip("/")

    for suffix in ("/api/v1/api/hosts", "/api/v1/api", "/api/v1", "/hosts"):
        if path.endswith(suffix):
            path = path[: -len(suffix)].rstrip("/")
            break

    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def normalize_hosts_url(api_url):
    """Return a hosts list URL without a trailing slash.

    Accepts either the full ``.../api/v1/api/hosts`` endpoint or an instance
    root such as ``https://patchmon.example.com``.
    """
    if not api_url:
        raise PatchMonAPIError("api_url is required")

    url = api_url.strip()
    parts = urlsplit(url)
    path = (parts.path or "").rstrip("/")

    if path.endswith("/api/v1/api/hosts") or path.endswith("/hosts"):
        normalized_path = path
    elif path.endswith("/api/v1/api"):
        normalized_path = path + "/hosts"
    elif path in ("", "/"):
        normalized_path = HOSTS_PATH
    else:
        # Treat as instance root with an optional base path prefix.
        normalized_path = path.rstrip("/") + HOSTS_PATH

    return urlunsplit((parts.scheme, parts.netloc, normalized_path, "", ""))


def build_hosts_url(api_url, include_stats=False, hostgroup=None):
    """Build the hosts list URL with optional query parameters."""
    base = normalize_hosts_url(api_url)
    params = []

    if include_stats:
        params.append(("include", "stats"))

    if hostgroup:
        if isinstance(hostgroup, (list, tuple)):
            value = ",".join(str(item) for item in hostgroup if item)
        else:
            value = str(hostgroup)
        if value:
            params.append(("hostgroup", value))

    if not params:
        return base
    return "{0}?{1}".format(base, urlencode(params))


def host_resource_url(api_url, host_id, resource=None, query=None):
    """Build a per-host resource URL under the Integration API."""
    base = normalize_hosts_url(api_url).rstrip("/")
    path = "{0}/{1}".format(base, host_id)
    if resource:
        path = "{0}/{1}".format(path, resource.lstrip("/"))
    if query:
        path = "{0}?{1}".format(path, urlencode(query))
    return path


def _format_http_error(url, response):
    detail = ""
    payload = None
    try:
        body = response.json()
        payload = body if isinstance(body, dict) else None
        if isinstance(body, dict):
            detail = body.get("error") or body.get("message") or ""
    except ValueError:
        detail = (response.text or "")[:200]

    message = "'{0}' returned HTTP {1}".format(url, response.status_code)
    if response.status_code == 401:
        message = "{0}: authentication failed (check credentials)".format(message)
    elif response.status_code == 403:
        message = (
            "{0}: access denied (missing API scope or enrollment permission)".format(
                message
            )
        )
    if detail:
        message = "{0}: {1}".format(message, detail)
    return message, payload


class _BaseClient(object):
    """Shared HTTP helpers."""

    def __init__(self, verify_ssl=True, timeout=30):
        if not HAS_REQUESTS:
            raise PatchMonAPIError(
                "The Python 'requests' library is required but not installed"
            )
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def _request(
        self,
        method,
        url,
        params=None,
        json_body=None,
        headers=None,
        allow_redirects=False,
        expect_json=True,
        ok_statuses=None,
    ):
        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=allow_redirects,
            )
        except requests.exceptions.RequestException as exc:
            raise PatchMonAPIError(
                "failed to {0} '{1}': {2}".format(method.upper(), url, exc)
            ) from exc

        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            raise PatchMonAPIError(
                "'{0}' returned redirect {1} to '{2}'. "
                "Use the final hosts URL without a trailing-slash redirect.".format(
                    url,
                    response.status_code,
                    response.headers.get("Location", ""),
                ),
                status_code=response.status_code,
            )

        ok = ok_statuses or ()
        if response.status_code >= 400 and response.status_code not in ok:
            message, payload = _format_http_error(url, response)
            raise PatchMonAPIError(
                message, status_code=response.status_code, payload=payload
            )

        if not expect_json:
            return response.text

        if not response.content:
            if response.status_code in (200, 201, 204) or response.status_code in ok:
                return {}
            raise PatchMonAPIError(
                "'{0}' returned an empty body (HTTP {1})".format(
                    url, response.status_code
                ),
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise PatchMonAPIError(
                "API did not return valid JSON (HTTP {0}, content-type {1})".format(
                    response.status_code,
                    response.headers.get("Content-Type", ""),
                ),
                status_code=response.status_code,
            ) from exc


class PatchMonClient(_BaseClient):
    """HTTP client for the PatchMon Integration API (Basic Auth)."""

    def __init__(self, api_url, api_key, api_secret, verify_ssl=True, timeout=30):
        super(PatchMonClient, self).__init__(verify_ssl=verify_ssl, timeout=timeout)
        if not api_url:
            raise PatchMonAPIError("api_url is required")
        if not api_key:
            raise PatchMonAPIError("api_key is required")
        if not api_secret:
            raise PatchMonAPIError("api_secret is required")

        self.api_url = api_url
        self._auth = HTTPBasicAuth(api_key, api_secret)

    def request(self, method, url, params=None, allow_redirects=False, json_body=None):
        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                auth=self._auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=allow_redirects,
            )
        except requests.exceptions.RequestException as exc:
            raise PatchMonAPIError(
                "failed to {0} '{1}': {2}".format(method.upper(), url, exc)
            ) from exc

        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            raise PatchMonAPIError(
                "'{0}' returned redirect {1} to '{2}'. "
                "Use the final hosts URL without a trailing-slash redirect.".format(
                    url,
                    response.status_code,
                    response.headers.get("Location", ""),
                ),
                status_code=response.status_code,
            )

        if response.status_code >= 400:
            message, payload = _format_http_error(url, response)
            raise PatchMonAPIError(
                message, status_code=response.status_code, payload=payload
            )

        if method.upper() == "DELETE" and (
            not response.content or response.status_code in (200, 204)
        ):
            if not response.content:
                return {"status_code": response.status_code}
            try:
                return response.json()
            except ValueError:
                return {"status_code": response.status_code, "text": response.text}

        if not response.content:
            raise PatchMonAPIError(
                "'{0}' returned an empty body (HTTP {1})".format(
                    url, response.status_code
                ),
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise PatchMonAPIError(
                "API did not return valid JSON (HTTP {0}, content-type {1})".format(
                    response.status_code,
                    response.headers.get("Content-Type", ""),
                ),
                status_code=response.status_code,
            ) from exc

    def get_hosts(self, include_stats=False, hostgroup=None):
        url = build_hosts_url(
            self.api_url, include_stats=include_stats, hostgroup=hostgroup
        )
        payload = self.request("GET", url)
        if not isinstance(payload, dict):
            raise PatchMonAPIError("expected a JSON object with a 'hosts' list")
        hosts = payload.get("hosts", [])
        if not isinstance(hosts, list):
            raise PatchMonAPIError("'hosts' must be a list")
        return payload

    def find_host(
        self, host_id=None, friendly_name=None, hostname=None, include_stats=False
    ):
        """Return the first matching host from the Integration list, or None."""
        payload = self.get_hosts(include_stats=include_stats)
        hosts = payload.get("hosts") or []
        for entry in hosts:
            if not isinstance(entry, dict):
                continue
            if host_id and str(entry.get("id")) == str(host_id):
                return entry
            if friendly_name and (
                (entry.get("friendly_name") or "").lower() == friendly_name.lower()
            ):
                return entry
            if hostname and (
                (entry.get("hostname") or "").lower() == hostname.lower()
            ):
                return entry
        return None

    def get_host_info(self, host_id):
        return self.request("GET", host_resource_url(self.api_url, host_id, "info"))

    def get_host_stats(self, host_id):
        return self.request("GET", host_resource_url(self.api_url, host_id, "stats"))

    def get_host_system(self, host_id):
        return self.request("GET", host_resource_url(self.api_url, host_id, "system"))

    def get_host_network(self, host_id):
        return self.request("GET", host_resource_url(self.api_url, host_id, "network"))

    def get_host_integrations(self, host_id):
        return self.request(
            "GET", host_resource_url(self.api_url, host_id, "integrations")
        )

    def get_host_packages(self, host_id, updates_only=False):
        query = {"updates_only": "true"} if updates_only else None
        return self.request(
            "GET",
            host_resource_url(self.api_url, host_id, "packages", query=query),
        )

    def get_host_notes(self, host_id):
        return self.request("GET", host_resource_url(self.api_url, host_id, "notes"))

    def delete_host(self, host_id):
        """Delete a host. Requires Integration scope ``host:delete``."""
        url = host_resource_url(self.api_url, host_id)
        return self.request("DELETE", url)


class PatchMonEnrollmentClient(_BaseClient):
    """Client for PatchMon Auto-Enrollment endpoints (header auth)."""

    def __init__(
        self,
        server_url,
        enrollment_key,
        enrollment_secret,
        verify_ssl=True,
        timeout=30,
    ):
        super(PatchMonEnrollmentClient, self).__init__(
            verify_ssl=verify_ssl, timeout=timeout
        )
        if not server_url:
            raise PatchMonAPIError("server_url is required")
        if not enrollment_key:
            raise PatchMonAPIError("enrollment_key is required")
        if not enrollment_secret:
            raise PatchMonAPIError("enrollment_secret is required")

        self.server_url = normalize_instance_url(server_url)
        self._headers = {
            "X-Auto-Enrollment-Key": enrollment_key,
            "X-Auto-Enrollment-Secret": enrollment_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path, query=None):
        base = self.server_url.rstrip("/") + path
        if query:
            return "{0}?{1}".format(base, urlencode(query))
        return base

    def enroll(
        self, friendly_name, machine_id=None, host_id=None, metadata=None
    ):
        """POST /api/v1/auto-enrollment/enroll — create or re-key a host entry."""
        body = {"friendly_name": friendly_name}
        if machine_id:
            body["machine_id"] = machine_id
        if host_id:
            body["host_id"] = host_id
        if metadata:
            body["metadata"] = metadata

        url = self._url(AUTO_ENROLLMENT_PATH + "/enroll")
        return self._request(
            "POST",
            url,
            json_body=body,
            headers=self._headers,
            ok_statuses=(409,),
        )

    def get_script(self, script_type="direct-host", force=False):
        """GET /api/v1/auto-enrollment/script — bash installer with injected creds."""
        query = {
            "type": script_type,
            "token_key": self._headers["X-Auto-Enrollment-Key"],
            "token_secret": self._headers["X-Auto-Enrollment-Secret"],
        }
        if force:
            query["force"] = "true"
        url = self._url(AUTO_ENROLLMENT_PATH + "/script", query=query)
        # Script endpoint uses query auth; omit secret headers from GET when possible.
        return self._request("GET", url, expect_json=False)


class PatchMonAdminClient(_BaseClient):
    """Admin JWT client for Auto-Enrollment token CRUD."""

    def __init__(self, server_url, admin_token, verify_ssl=True, timeout=30):
        super(PatchMonAdminClient, self).__init__(
            verify_ssl=verify_ssl, timeout=timeout
        )
        if not server_url:
            raise PatchMonAPIError("server_url is required")
        if not admin_token:
            raise PatchMonAPIError("admin_token is required")

        self.server_url = normalize_instance_url(server_url)
        self._headers = {
            "Authorization": "Bearer {0}".format(admin_token),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path):
        return self.server_url.rstrip("/") + path

    def create_enrollment_token(
        self,
        token_name,
        max_hosts_per_day=100,
        default_host_group_id=None,
        allowed_ip_ranges=None,
        expires_at=None,
        metadata=None,
    ):
        """POST /api/v1/auto-enrollment/tokens — requires Manage Settings JWT."""
        body = {
            "token_name": token_name,
            "max_hosts_per_day": max_hosts_per_day,
        }
        if default_host_group_id:
            body["default_host_group_id"] = default_host_group_id
        if allowed_ip_ranges:
            body["allowed_ip_ranges"] = allowed_ip_ranges
        if expires_at:
            body["expires_at"] = expires_at
        if metadata:
            body["metadata"] = metadata

        return self._request(
            "POST",
            self._url(AUTO_ENROLLMENT_PATH + "/tokens"),
            json_body=body,
            headers=self._headers,
        )

    def delete_enrollment_token(self, token_id):
        return self._request(
            "DELETE",
            self._url(AUTO_ENROLLMENT_PATH + "/tokens/{0}".format(token_id)),
            headers=self._headers,
        )

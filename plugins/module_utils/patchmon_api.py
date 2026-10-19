# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared PatchMon Integration API client helpers."""

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


class PatchMonAPIError(Exception):
    """Raised when a PatchMon API call fails."""

    def __init__(self, message, status_code=None):
        super(PatchMonAPIError, self).__init__(message)
        self.status_code = status_code


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


class PatchMonClient(object):
    """Minimal HTTP client for the PatchMon Integration API."""

    def __init__(self, api_url, api_key, api_secret, verify_ssl=True, timeout=30):
        if not HAS_REQUESTS:
            raise PatchMonAPIError(
                "The Python 'requests' library is required but not installed"
            )
        if not api_url:
            raise PatchMonAPIError("api_url is required")
        if not api_key:
            raise PatchMonAPIError("api_key is required")
        if not api_secret:
            raise PatchMonAPIError("api_secret is required")

        self.api_url = api_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._auth = HTTPBasicAuth(api_key, api_secret)
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def request(self, method, url, params=None, allow_redirects=False):
        try:
            response = self._session.request(
                method,
                url,
                params=params,
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
            detail = ""
            try:
                body = response.json()
                if isinstance(body, dict):
                    detail = body.get("error") or body.get("message") or ""
            except ValueError:
                detail = (response.text or "")[:200]
            message = "'{0}' returned HTTP {1}".format(url, response.status_code)
            if detail:
                message = "{0}: {1}".format(message, detail)
            raise PatchMonAPIError(message, status_code=response.status_code)

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

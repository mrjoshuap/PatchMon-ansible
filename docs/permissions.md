# PatchMon API permissions for this collection

PatchMon uses **different credential types** for different operations. Using the wrong type produces HTTP 401/403 errors that look like “bad password” when the real issue is scope or auth model.

## Credential types

| Type | Auth | Where created | Used for |
|------|------|---------------|----------|
| **Integration API** | HTTP Basic (`api_key`:`api_secret`) | Settings → Integrations → **API** | Inventory, `host_info`, `host_packages`, lookup, host delete |
| **Auto-Enrollment** | `X-Auto-Enrollment-Key` / `X-Auto-Enrollment-Secret` (or script query params) | Settings → Integrations → **Auto-Enrollment** | Create host entries, download install script, `agent` / `host` roles |
| **Admin session JWT** | `Authorization: Bearer …` | Logged-in admin session | Create/delete enrollment tokens (`host_token` state=present/absent) |
| **Per-host agent creds** | `X-API-ID` / `X-API-KEY` | Returned once at enrollment | Agent communication (not used directly by most collection modules) |

Integration API credentials are **not** the same as UI session RBAC. Compliance routes under `/api/v1/compliance/*` remain session-scoped; see [PatchMon/PatchMon#1189](https://github.com/PatchMon/PatchMon/issues/1189).

## Integration API scopes

Scopes are explicit. `get` does **not** imply `delete`.

| Scope | Capabilities in this collection |
|-------|----------------------------------|
| `host:get` | Inventory plugin, `host_info`, `host_packages`, `lookup('patchmon.ansible.host')`, existence checks before enroll |
| `host:delete` | `patchmon.ansible.host` with `state=absent`, `roles/host` when `host_state=absent` |

There is **no** Integration `host:create` scope. Host creation uses the **Auto-Enrollment** API.

## Auto-Enrollment

| Capability | Auth | Consumers |
|------------|------|-----------|
| Enroll host (`POST …/auto-enrollment/enroll`) | Enrollment key/secret | Module `host` (`state=present`), role `host` |
| Fetch install script (`GET …/auto-enrollment/script`) | Enrollment key/secret | Module `host_token` (`state=script`), role `agent` |
| Create/delete enrollment tokens | Admin JWT (Manage Settings) | Module `host_token` (`state=present`/`absent`) |

Enrollment returns a one-time host `api_key`. Treat it as a secret (`no_log` on tasks).

## Least-privilege guidance

1. **Read-only automation** (inventory, reporting playbooks): Integration token with **only** `host:get`.
2. **Provisioning** (create hosts / install agents): dedicated Auto-Enrollment token with IP allow lists and daily host limits where possible.
3. **Decommission** (delete hosts): separate Integration token with `host:get` + `host:delete`, or a tightly controlled job; never share delete tokens with inventory-only projects.
4. **Token minting** (create enrollment tokens from Ansible): admin JWT only on trusted Controllers; prefer creating tokens in the UI and injecting key/secret via Vault / AAP credentials.
5. Store secrets in Ansible Vault, AAP Credential, or environment variables — **never** commit plaintext keys.
6. Keep `verify_ssl: true` outside lab environments.

## HTTP status quick reference

| Status | Likely cause |
|--------|----------------|
| 401 | Wrong key/secret, or using Integration creds on Auto-Enrollment (or vice versa) |
| 403 | Missing scope (`host:get` / `host:delete`) or enrollment IP not allowed |
| 409 | Host already enrolled / machine_id conflict (often safe to treat as “already present”) |
| 429 | Enrollment rate limit or re-enroll cooldown |

## Per-plugin summary

| Plugin / role | Minimum access |
|---------------|----------------|
| `patchmon.ansible.inventory` | Integration `host:get` |
| `patchmon.ansible.host_info` / `host_packages` / lookup `host` | Integration `host:get` |
| `patchmon.ansible.host` present | Auto-Enrollment token |
| `patchmon.ansible.host` absent | Integration `host:delete` |
| `patchmon.ansible.host_token` script | Auto-Enrollment token |
| `patchmon.ansible.host_token` present/absent | Admin JWT (Manage Settings) |
| `patchmon.ansible.agent` | Auto-Enrollment token (install) |
| `patchmon.ansible.host` role | See table above by `host_state` |

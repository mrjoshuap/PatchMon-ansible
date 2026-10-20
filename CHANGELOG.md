# Changelog

All notable changes to this collection are documented in this file.

## [2.0.0-rc1] - 2026-10-20

### Added

- `patchmon.core.host` desired-state fields (`friendly_name_update`, `notes`,
  `auto_update`, `host_down_alerts`, `groups`). Omitted fields are not sent.
  Compares use `host:get`; scalar writes use `host:patch`; group replacement
  uses `host:put`.
- `patchmon.core.host_action` for `fetch_report`, `force_agent_update`, and
  `regenerate_credentials` (`host:update`).
- `host` role variables for the same desired-state fields. They stay unmanaged
  until set.

- Integration `host:get` reads for `package_reports` and `agent_queue` on the
  API client, `host_info`, and the `host` lookup. `host_info` also gathers
  `notes`.
- `report_health` role fails when the newest package report is missing or not
  `success`.

### Changed

- Inventory host groups are named `patchmon_<slug>` so they sort with the
  stats groups. Spaces and other characters Ansible rejects become `_`, then
  the name is lowercased (`No Reboot` → `patchmon_no_reboot`). The original
  name and id are hostvar `patchmon_groups` and group vars
  `patchmon_group_name` / `patchmon_group_id`. A slug shared by two groups,
  or one that matches a stats auto-group, appends the group id. `host`
  membership and the inventory `hostgroup` filter accept an exact name
  (spaces kept), a group id, or that Ansible group. A sanitized token that
  matches both a space and an underscore must be the id or the exact name.

### Fixed

- `host` role `host_fetch_script` passes `dest` to `host_token`, which requires
  it for `state=script`.

## [2.0.0-charlie] - 2026-10-19

### Changed

- `get_script`: pass enrollment `token_key` / `token_secret` via requests
  `params` instead of embedding them in the URL string, so API error messages
  and client logs do not capture credentials.

## [2.0.0-beta] - 2026-10-19

### Added

- `agent` role: `agent_keep_failed_script` / `agent_failed_script_path` to retain
  the enrollment script on install failure for debugging; remove staged script
  after a successful install.
- `host_token` `dest` option (required for `state=script`) writes the installer
  to a file instead of returning the script body.

### Fixed

- Agent install 401 `Invalid or inactive token` caused by Ansible `no_log`
  replacing enrollment key/secret substrings inside registered `script` with
  literal `********`. Role now copies from `dest` on the controller.

## [2.0.0] - 2026-10-19

Collection renamed from `patchmon.dynamic_inventory` to `patchmon.core`.
Install with `ansible-galaxy collection install patchmon.core`.

**This release is not backward compatible.** Update inventory `plugin:` values and
FQCN references. See [docs/migrating_to_2.0.md](docs/migrating_to_2.0.md).

### Breaking

- Collection FQCN is now `patchmon.core` (was `patchmon.dynamic_inventory`).
- Inventory plugin is `patchmon.core.inventory` (was
  `patchmon.dynamic_inventory.dynamic_inventory`).
- No FQCN redirects or shim collections are provided.

### Added

- Inventory option `include_stats` (`?include=stats`), namespaced `patchmon_*`
  hostvars, auto groups, Constructable support, cache, and related options.
- Shared `module_utils.patchmon_api` client (Integration + Auto-Enrollment + admin JWT).
- Modules: `host_info`, `host_packages`, `host`, `host_token`.
- Lookup: `host`.
- Roles: `agent`, `host` with `tasks/validate.yml` and thin `playbooks/`.
- Docs: `docs/permissions.md`, `docs/migrating_to_2.0.md`.
- Auth documentation fragment; examples, unit tests, CI and release workflows.
- `meta/runtime.yml` `action_groups.patchmon` for `module_defaults`.

### Changed

- Inventory uses `_read_config_data` / `get_option` and Ansible safe group names.
- `requires_ansible` is `>=2.15.0`.
- Auth docs cover Integration scopes vs Auto-Enrollment and least privilege.

### Notes

- Compliance metadata is not yet available on the scoped Integration API; tracked
  upstream in [PatchMon/PatchMon#1189](https://github.com/PatchMon/PatchMon/issues/1189).

## [1.0.0] - 2025-11-12

Initial release as `patchmon.dynamic_inventory`: Integration API dynamic inventory plugin only.

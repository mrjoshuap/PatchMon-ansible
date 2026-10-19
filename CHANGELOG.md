# Changelog

All notable changes to this collection are documented in this file.

## [Unreleased]

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

# Changelog

All notable changes to this collection are documented in this file.

## [1.1.0] - 2026-10-19

### Added

- Inventory option `include_stats` to request `GET /api/v1/api/hosts?include=stats` and expose namespaced hostvars (`patchmon_needs_reboot`, `patchmon_update_state`, `patchmon_security_updates_count`, OS/reporting fields, and more).
- Built-in auto groups when stats are enabled (`patchmon_needs_reboot`, `patchmon_security_required`, `patchmon_updates_pending`, `patchmon_up_to_date`, `patchmon_stale`, `patchmon_overdue`, `patchmon_inactive`, `patchmon_os_*`).
- Constructable inventory support: `compose`, `groups`, `keyed_groups`, `strict`, `leading_separator`, `use_extra_vars`.
- Inventory options: `hostgroup`, `auto_groups`, `inventory_hostname_prefer`, `timeout`, and native `env`/`ini` credential options.
- Inventory cache support via Ansible inventory cache plugins.
- Shared `module_utils.patchmon_api` client used by inventory, modules, and lookups.
- Modules: `patchmon_host_info`, `patchmon_host_packages`.
- Lookup: `patchmon_host`.
- Example inventory files under `examples/`.
- Unit tests for API helpers and inventory population.

### Changed

- Inventory plugin now uses `_read_config_data` / `get_option` instead of a manual YAML load.
- Group names are sanitized with Ansible's safe group name helper.
- `requires_ansible` lowered to `>=2.15.0` to widen adoption while retaining constructed inventory features.

### Notes

- Compliance metadata is not yet available on the scoped Integration API; tracked upstream in [PatchMon/PatchMon#1189](https://github.com/PatchMon/PatchMon/issues/1189).

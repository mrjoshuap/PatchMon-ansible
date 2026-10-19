# Changelog

All notable changes to this collection are documented in this file.

## [Unreleased]

### Added

- Shared documentation fragment `patchmon.ansible.auth` for API connection options across inventory, modules, and lookup.
- Unit tests for `patchmon_host_info`, `patchmon_host_packages`, and the `patchmon_host` lookup.
- GitHub Actions CI workflow (pytest + ansible-lint on example playbooks).

### Changed

- README documents the correct inventory `plugin` value (`patchmon.ansible.dynamic_inventory`).
- Inventory, modules, and lookup mark both `api_key` and `api_secret` as `no_log` via the auth fragment.
- README and inventory docs clarify unprefixed compose aliases (`ip`, `hostname`, `friendly_name`) vs preferred `patchmon_*` hostvars.

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
- Example inventory files under `examples/` (`patchmon_inventory.yml` minimal; `patchmon_inventory_stats.yml` stats + Constructable).
- Example playbooks under `examples/playbooks/` for `patchmon_host_info`, `patchmon_host_packages`, and the `patchmon_host` lookup (inventory-driven and UUID-only).
- [`examples/README.md`](examples/README.md) walkthrough: prerequisites, inventory + playbook usage, minimal vs stats comparison, and troubleshooting.
- GitHub Actions [Release collection](.github/workflows/release.yml) workflow: on `vX.Y.Z` tags, run tests, build the collection tarball, and attach it to a GitHub Release for offline installs.
- Unit tests for API helpers and inventory population.

### Changed

- **Collection renamed** from `patchmon.dynamic_inventory` to `patchmon.ansible` so modules and lookups are not namespaced under an inventory-only collection. Install with `ansible-galaxy collection install patchmon.ansible`. Module FQCNs are now `patchmon.ansible.patchmon_host_info` (and similarly for packages/lookup); the inventory plugin is `patchmon.ansible.dynamic_inventory`.
- Inventory plugin now uses `_read_config_data` / `get_option` instead of a manual YAML load.
- Group names are sanitized with Ansible's safe group name helper.
- `requires_ansible` lowered to `>=2.15.0` to widen adoption while retaining constructed inventory features.
- Example inventories expanded with guided comments (active minimal defaults; optional options commented).
- README documents offline install from release assets, “Using the examples”, and how to cut a tagged release.

### Notes

- Compliance metadata is not yet available on the scoped Integration API; tracked upstream in [PatchMon/PatchMon#1189](https://github.com/PatchMon/PatchMon/issues/1189).

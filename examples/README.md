# Examples

Copy-paste inventory files and playbooks for `patchmon.core`.

Install, credentials, the first inventory, fleet plays, and troubleshooting are chapters of the [Automator guide](../docs/automator-guide.md). This page is the file index.

## Inventory templates

Heavily commented: required options are active; everything else is commented with guidance.

| File | Use when |
|------|----------|
| [`patchmon_inventory.yml`](patchmon_inventory.yml) | Minimal / v1.0-compatible inventory (hosts, IPs, PatchMon groups only) |
| [`patchmon_inventory_stats.yml`](patchmon_inventory_stats.yml) | Data-rich inventory (`include_stats`) with auto groups and optional Constructable blocks |

## Playbooks (modules and lookup)

| File | What it demonstrates |
|------|----------------------|
| [`playbooks/host_info.yml`](playbooks/host_info.yml) | `host_info` against inventory hosts (`patchmon_id`) |
| [`playbooks/pending_updates.yml`](playbooks/pending_updates.yml) | `host_packages` with `updates_only`, security versus other updates |
| [`playbooks/host_info_by_id.yml`](playbooks/host_info_by_id.yml) | Both modules on `localhost` with `-e patchmon_id=...` (no dynamic inventory) |
| [`playbooks/lookup_system.yml`](playbooks/lookup_system.yml) | `host` lookup for system, stats, pending packages, package reports, and the agent queue |

## Fleet lifecycle

These match [Fleet lifecycle](../docs/automator-guide.md#chapter-6-fleet-lifecycle). Run maintain, all-pending upgrades, and retire against a stats inventory. `Automated` and `No Reboot` must exist in PatchMon so `patchmon_automated` and `patchmon_no_reboot` are in the inventory.

| File | What it does |
|------|----------------|
| [`playbooks/enroll.yml`](playbooks/enroll.yml) | Install the agent (`agent_state: present`). The host stays in the enrollment token's default group |
| [`playbooks/maintain.yml`](playbooks/maintain.yml) | Refresh inventory, report health, security-only updates, reboot Automated one host at a time |
| [`playbooks/report_health.yml`](playbooks/report_health.yml) | Import `patchmon.core.report_health` |
| [`playbooks/apply_security_updates.yml`](playbooks/apply_security_updates.yml) | Import `patchmon.core.apply_security_updates` |
| [`playbooks/reboot_needed.yml`](playbooks/reboot_needed.yml) | Import `patchmon.core.reboot_needed` |
| [`playbooks/apply_all_updates.yml`](playbooks/apply_all_updates.yml) | Import `patchmon.core.apply_all_updates`. Not part of maintain |
| [`playbooks/retire.yml`](playbooks/retire.yml) | Remove the agent, then delete the host when `patchmon_id` is set. Requires `--limit` |

Thin plays for the agent and host roles live next to the collection, not in this directory: [`playbooks/agent.yml`](../playbooks/agent.yml) and [`playbooks/host.yml`](../playbooks/host.yml).

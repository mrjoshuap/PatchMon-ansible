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
| [`playbooks/enroll.yml`](playbooks/enroll.yml) | On the control node, add the host when it is missing from the inventory, then install the agent (`agent_state: present`). The host stays in the enrollment token's default group |
| [`playbooks/maintain.yml`](playbooks/maintain.yml) | Refresh inventory, report health, security updates by default (`-e apply_all_updates=true` for all pending), reboot Automated one host at a time |
| [`playbooks/report_health.yml`](playbooks/report_health.yml) | Import `patchmon.core.report_health` |
| [`playbooks/apply_security_updates.yml`](playbooks/apply_security_updates.yml) | Import `patchmon.core.apply_security_updates` |
| [`playbooks/reboot_needed.yml`](playbooks/reboot_needed.yml) | Import `patchmon.core.reboot_needed` |
| [`playbooks/apply_all_updates.yml`](playbooks/apply_all_updates.yml) | Import `patchmon.core.apply_all_updates`. `maintain.yml` imports this play when `-e apply_all_updates=true` |
| [`playbooks/retire.yml`](playbooks/retire.yml) | Remove the agent, then delete the host when `patchmon_id` is set. Requires `--limit` |

Thin plays for the agent and host roles live next to the collection, not in this directory: [`playbooks/agent.yml`](../playbooks/agent.yml) and [`playbooks/host.yml`](../playbooks/host.yml).

## Demo Script

In this demonstration, we have valid API and enrollment keys with the necessary permissions for PatchMon. We’ve already followed the Developer Guide and have our development container running with PatchMon-related environment variables configured. Our demo host, `patchmon-test` (IP: 192.168.8.20), is prepared with SSH keys and passwordless sudo access. At this stage, the host has not yet been added to the PatchMon inventory.

Let’s confirm this by inspecting the current inventory:

```
ansible-inventory --graph
ansible-inventory --graph | grep patchmon-test
ansible-inventory --host patchmon-test
```

Since the host does not appear in the inventory and we don’t have DNS set up, let’s enroll it directly using its IP address:

```
ansible-playbook examples/playbooks/enroll.yml -e enroll_host=192.168.8.20
```

After enrollment completes, let’s verify that the host is now part of the inventory, I'm going to use jq to filter out the non-patchmon related ones:

```
ansible-inventory --host patchmon-test | jq 'with_entries(select(.key | startswith("patchmon_")))'
```

The host is ready—we can immediately begin automating tasks with Ansible. For example, check connectivity:

```
ansible -m ping patchmon-test
```

For ongoing management, you might schedule the `maintain.yml` playbook or trigger it as needed with Ansible limits. For this demo, let’s run maintenance against just our test instance:

```
ansible-playbook examples/playbooks/maintain.yml --limit patchmon-test
```

You’ll notice that all tasks are skipped initially. This is expected—newly enrolled systems are not automatically patched by default. This allows us to control when they become fully managed.

To see the group assignment, check which manual hosts are present:

```
ansible-inventory --graph patchmon_manual
```

Next, let’s open the PatchMon interface, assign the appropriate groups to our new system, and then re-run the maintenance playbook:

```
ansible-playbook examples/playbooks/maintain.yml --limit patchmon-test
```

By default, this playbook only applies security updates. If you want to apply all pending updates instead, simply include the `apply_all_updates=true` extra variable:

```
ansible-playbook examples/playbooks/maintain.yml --limit patchmon-test -e apply_all_updates=true
```

Eventually, when you need to decommission the host, you can retire it with the following commands and verify its removal from the inventory:

```
ansible-playbook examples/playbooks/retire.yml --limit patchmon-test
ansible-inventory --host patchmon-test
```

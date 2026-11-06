# Announcement

**`patchmon.core` 2.x is the official Ansible collection for PatchMon**

## Summary

`patchmon.core` replaces `patchmon.dynamic_inventory` 1.0.0 as the official Ansible collection. The older collection was a dynamic inventory plugin only. Ansible workflows for inventory, agent rollout, and scheduled patching need more than a host list: groups and stats to target, a way to enroll and manage the agent, and a way to read or update host state from a play.

`patchmon.core` provides that. It is a breaking change for anyone still on 1.0.0. The break is the dynamic inventory: the collection name and the plugin name. 2.x does not ship an FQCN redirect. Install `patchmon.core` and set `plugin: patchmon.core.inventory`. The modules, roles, lookup, and inventory filters are new, so they do not change an existing 1.0.0 inventory file beyond that plugin line.

## Install

```bash
ansible-galaxy collection install patchmon.core
pip install 'requests>=2.25.1'
```

Air-gapped installs can use the release tarball from [GitHub Releases](https://github.com/PatchMon/PatchMon-ansible/releases). Details: [Automator guide, Install](https://patchmon.github.io/PatchMon-ansible/docsite/automator_guide.html#chapter-2-install).

## Migrating from 1.0

Current users change two names:

- Collection: `patchmon.dynamic_inventory` becomes `patchmon.core`
- Inventory plugin: `patchmon.dynamic_inventory.dynamic_inventory` becomes `patchmon.core.inventory`

Migration, with the inventory snippet: [Migrating from 1.0](https://patchmon.github.io/PatchMon-ansible/docsite/automator_guide.html#chapter-9-migrating-from-1-0)

## What 2.x provides

- Inventory with optional stats hostvars (`include_stats`), `patchmon_*` groups for policy and for state (security updates, reboot, reporting), a `hostgroup` filter, and constructed inventory (`compose`, `groups`, `keyed_groups`)
- Modules: `host`, `host_info`, `host_packages`, `host_token`, `host_agent_script`
- Lookups: `host`, `endpoint`
- Roles: `agent` (install, start, stop, report, remove), `host` (enroll or delete), `report_health`, `apply_security_updates`, `apply_all_updates`, `reboot_needed`, plus maintenance helpers (`package_cleanup`, `restart_services`, `kernel_cleanup`, `package_held`, `package_changelog`)
- A documented split between Integration credentials (`host:get` for reads, `host:delete` to remove a host) and Auto-Enrollment (create a host and install the agent)
- Host field changes, group replacement, and host commands are left out until the Integration API has them. Paste-ready requests: [PATCHMON-FEEDBACK.md](PATCHMON-FEEDBACK.md)

The plugin, role, and guide pages are published here: [patchmon.core documentation](https://patchmon.github.io/PatchMon-ansible/)

Credentials: [Automator guide, Credentials](https://patchmon.github.io/PatchMon-ansible/docsite/automator_guide.html#chapter-3-credentials)

First inventory: [Automator guide, First inventory](https://patchmon.github.io/PatchMon-ansible/docsite/automator_guide.html#chapter-4-first-inventory)

Inventory plugin: [patchmon.core.inventory](https://patchmon.github.io/PatchMon-ansible/inventory_inventory.html)

Repository: [PatchMon/PatchMon-ansible](https://github.com/PatchMon/PatchMon-ansible)

## Why

Those three requests are one workflow. An existing Ansible estate needs PatchMon as the inventory, a role that rolls the agent out with Auto-Enrollment, and hostvars so a scheduled play can patch one group and reboot another. The 1.0.0 plugin answered the first part. The modules, roles, lookup, and inventory filters make the rest repeatable, and they are documented on the docsite so someone can use them without reading the source.

The collection follows [Red Hat Automation Good Practices](https://redhat-cop.github.io/automation-good-practices/): defaults, validation, idempotent tasks, and thin playbooks in front of the roles. pytest covers the inventory, modules, lookup, and API client. ansible-lint covers the playbook and role YAML. Collection documentation lint publishes as the docsite. Roles ship argument specs (`meta/argument_specs.yml`) and `tasks/validate.yml`.

## Related requests this covers

These feedback-portal requests are covered by the collection:

- [Ansible Dynamic Inventory](https://feedback.patchmon.net/b/feature-requests/posts/post_01kyzbkqs5fzst21twgbqvnze2). `patchmon.core.inventory` lists hosts, groups, and optional stats hostvars.
- [Automatic rollout of agents via API with Ansible](https://feedback.patchmon.net/b/feature-requests/posts/post_01kyze5xncfzst242c0107agdf). `patchmon.core.agent` enrolls a host and installs, starts, stops, reports, or removes the agent.
- [Patch Management using Ansible](https://feedback.patchmon.net/b/feature-requests/posts/post_01kyz5ctqsenfvfjamcjdyxmqf). Policy groups and hostvars such as `patchmon_update_state` and `patchmon_needs_reboot` let a play patch and reboot selected hosts on a schedule. PatchMon stays the source of group membership.

The adoption write-up that led to this collection is on the [feedback portal](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5fj33qte04r3x9v6527stma).

Compliance is a separate product change, and this collection leaves it out:

- [Expose compliance summary on the Integration API](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5aw69zbe04r3hm0efeedbxj)

Those routes are session RBAC today. Once they exist on the Integration API, a later release can map them.

## AI disclosure

- **Used AI:** yes
- **Model(s):** Grok
- **Harness / tool:** Cursor
- **Scope:** collection code, tests, docs, and this announcement, guided by Ansible best-practice skills for collections, roles, playbooks, and Python plugins
- **Human review completed:** yes

# Proposal

**Adopt patchmon.core 2.0 as the official Ansible collection**

## Please upvote

This request is open on the PatchMon feedback portal:

**[Adopt patchmon.core 2.0 as the official Ansible collection](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5fj33qte04r3x9v6527stma)**

If this collection would help your Ansible estate, please upvote that post. An upvote tells PatchMon that Ansible users want `patchmon.core` 2.0 adopted as the official collection. [How the feedback portal works](https://feedback.patchmon.net/hc/en/articles/9-how-the-feedback-portal-works) covers signing in and voting.

## Summary

The published Ansible collection is still `patchmon.dynamic_inventory` 1.0.0: a dynamic inventory plugin, and only that. The Ansible ideas already on the feedback board (inventory, agent rollout, and scheduled patching) need more than a host list. They need groups and stats to target, a way to enroll and manage the agent, and a way to read or update host state from a play.

I have that as `patchmon.core` 2.0.0 on my fork. It is a breaking change for the existing collection, and the break is the dynamic inventory: the collection name and the plugin name. 2.0.0 does not ship an FQCN redirect. Anyone on 1.0.0 installs `patchmon.core` and sets `plugin: patchmon.core.inventory`. The modules, roles, lookup, and inventory filters are new, so they do not change an existing 1.0.0 inventory file beyond that plugin line.

I am running 2.0.0 in my homelab from the offline release tarball.

## Proposal

Please consider adopting `patchmon.core` 2.0.0 as the official Ansible collection, in place of `patchmon.dynamic_inventory` 1.0.0.

Current users change two names:

- Collection: `patchmon.dynamic_inventory` becomes `patchmon.core`
- Inventory plugin: `patchmon.dynamic_inventory.dynamic_inventory` becomes `patchmon.core.inventory`

Migration, with the inventory snippet: [Migrating to patchmon.core 2.0.0](https://mrjoshuap.github.io/PatchMon-ansible/docsite/migrating_to_2.0.html)

What 2.0.0 adds for advanced Ansible users:

- Inventory with optional stats hostvars (`include_stats`), `patchmon_*` groups for policy and for state (security updates, reboot, reporting), a `hostgroup` filter, and constructed inventory (`compose`, `groups`, `keyed_groups`)
- Modules: `host`, `host_info`, `host_packages`, `host_token`
- Lookup: `host`
- Roles: `agent` (install, start, stop, report, remove), `host` (enroll or delete), `report_health`
- A documented split between Integration credentials (`host:get` for reads, `host:delete` to remove a host) and Auto-Enrollment (create a host and install the agent)
- Host field changes, group replacement, and host commands are left out until the Integration API has them. Paste-ready requests: [PATCHMON-FEEDBACK.md](PATCHMON-FEEDBACK.md)

Releases after 2.0.0 add roles `apply_security_updates`, `apply_all_updates`, and `reboot_needed`. The example plays of the same name import them.

The plugin, role, and guide pages are published here: [patchmon.core documentation](https://mrjoshuap.github.io/PatchMon-ansible/)

Permissions: [PatchMon API permissions](https://mrjoshuap.github.io/PatchMon-ansible/docsite/permissions.html)

Quick start: [Quick start](https://mrjoshuap.github.io/PatchMon-ansible/docsite/quick_start.html)

Inventory plugin: [patchmon.core.inventory](https://mrjoshuap.github.io/PatchMon-ansible/inventory_inventory.html)

Fork: [mrjoshuap/PatchMon-ansible](https://github.com/mrjoshuap/PatchMon-ansible)

Release I install, including the offline tarball: [patchmon.core 2.0.0](https://github.com/mrjoshuap/PatchMon-ansible/releases/tag/v2.0.0)

Upstream collection today (`patchmon.dynamic_inventory` 1.0.0): [PatchMon/PatchMon-ansible](https://github.com/PatchMon/PatchMon-ansible)

## Why

Those three requests are one workflow. An existing Ansible estate needs PatchMon as the inventory, a role that rolls the agent out with Auto-Enrollment, and hostvars so a scheduled play can patch one group and reboot another. The 1.0.0 plugin answers the first part. The modules, roles, lookup, and inventory filters are what make the rest repeatable, and they are documented on the docsite above so someone can use them without reading the source.

I have been running 2.0.0 this way in my homelab, installed from the release tarball rather than Galaxy:

```bash
ansible-galaxy collection install ./patchmon-core-2.0.0.tar.gz
```

Direct asset: [patchmon-core-2.0.0.tar.gz](https://github.com/mrjoshuap/PatchMon-ansible/releases/download/v2.0.0/patchmon-core-2.0.0.tar.gz)

It is in daily use. There may still be a couple of typos.

On the fork itself:

- pytest unit tests for the inventory, modules, lookup, and API client
- ansible-lint on the playbook and role YAML
- collection documentation lint, published as the docsite
- role argument specs (`meta/argument_specs.yml`), module argument specs, and `tasks/validate.yml` on each role
- collection layout following [Red Hat Automation Good Practices](https://redhat-cop.github.io/automation-good-practices/): defaults, validation, idempotent tasks, and thin playbooks in front of the roles

I developed it in Cursor with Grok, using Ansible best-practice skills for collections, roles, playbooks, and Python plugins. I run what I am asking you to adopt, and I can answer review questions on it.

## Related requests this can cover

Please upvote the [adoption request](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5fj33qte04r3x9v6527stma). If you accept the collection, these look covered:

- [Ansible Dynamic Inventory](https://feedback.patchmon.net/b/feature-requests/posts/post_01kyzbkqs5fzst21twgbqvnze2). `patchmon.core.inventory` lists hosts, groups, and optional stats hostvars.
- [Automatic rollout of agents via API with Ansible](https://feedback.patchmon.net/b/feature-requests/posts/post_01kyze5xncfzst242c0107agdf). `patchmon.core.agent` enrolls a host and installs, starts, stops, reports, or removes the agent.
- [Patch Management using Ansible](https://feedback.patchmon.net/b/feature-requests/posts/post_01kyz5ctqsenfvfjamcjdyxmqf). Policy groups and hostvars such as `patchmon_update_state` and `patchmon_needs_reboot` let a play patch and reboot selected hosts on a schedule. PatchMon stays the source of group membership.

Compliance is a separate product change, and this collection leaves it out:

- [Expose compliance summary on the Integration API](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5aw69zbe04r3hm0efeedbxj)

Those routes are session RBAC today. Once they exist on the Integration API, a later release can map them.

## AI disclosure

- **Used AI:** yes
- **Model(s):** Grok
- **Harness / tool:** Cursor
- **Scope:** collection code, tests, docs, and this request, guided by Ansible best-practice skills for collections, roles, playbooks, and Python plugins
- **Human review completed:** yes. I run `patchmon.core` 2.0.0 from the v2.0.0 tarball in my homelab. Expect a typo or two.

# Ansible Collection - patchmon.core

Dynamic inventory, modules, lookups, and roles for the [PatchMon](https://patchmon.net) Integration and Auto-Enrollment APIs.

The narrative for playbook authors is the **[Automator guide](docs/automator-guide.md)**. People changing this repository should read the **[Developer guide](docs/developer-guide.md)**. Published pages: [patchmon.core documentation](https://mrjoshuap.github.io/PatchMon-ansible/).

## Description

The `inventory` plugin turns PatchMon hosts and host groups into a live Ansible inventory. With `include_stats: true` it also exposes reboot, update, security, OS, and reporting metadata as host variables and optional auto groups, so you can target fleets with `--limit patchmon_security_required`.

| Type | FQCN | Purpose |
|------|------|---------|
| Inventory | `patchmon.core.inventory` | List hosts, groups, and stats hostvars |
| Module | `patchmon.core.host_info` | Aggregate `/info`, `/stats`, `/notes`, `/package_reports`, `/agent_queue`, and related routes |
| Module | `patchmon.core.host_packages` | List packages, optionally updates only |
| Module | `patchmon.core.host` | Enroll or delete a host entry |
| Module | `patchmon.core.host_token` | Enrollment script and admin token CRUD |
| Lookup | `patchmon.core.host` | Ad-hoc per-host API lookups |
| Lookup | `patchmon.core.endpoint` | Derive the hosts and auto-enrollment URLs |
| Role | `patchmon.core.agent` | Install, start, stop, report, or remove the agent |
| Role | `patchmon.core.host` | Create or delete host entries |
| Role | `patchmon.core.report_health` | Fail unless the newest package report succeeded |
| Role | `patchmon.core.apply_security_updates` | Security-only package updates, then a local agent report |
| Role | `patchmon.core.apply_all_updates` | All pending package upgrades, then a local agent report |
| Role | `patchmon.core.reboot_needed` | Reboot when `patchmon_needs_reboot` is true, then a local agent report |

Read plugins need Integration `host:get`. Creating hosts and installing agents need Auto-Enrollment credentials. See [Credentials](docs/automator-guide.md#chapter-3-credentials).

Upgrading from 1.0.0 (`patchmon.dynamic_inventory`) is a breaking change. Install `patchmon.core` and set `plugin:` to `patchmon.core.inventory`. See [Migrating from 1.0](docs/automator-guide.md#chapter-9-migrating-from-1-0).

Copy-paste inventories and plays: **[examples/README.md](examples/README.md)**.

## Requirements

- **Ansible**: >= 2.15.0
- **Python**: 3.9+
- **Dependencies**: `requests >= 2.25.1`

## Installation

### Ansible Galaxy

```bash
ansible-galaxy collection install patchmon.core
pip install 'requests>=2.25.1'
```

### Offline / air-gapped (GitHub Release tarball)

Tagged releases publish `patchmon-core-<version>.tar.gz` as a release asset. Download it from [Releases](https://github.com/PatchMon/PatchMon-ansible/releases), copy it to the target system, and install:

```bash
ansible-galaxy collection install ./patchmon-core-2.0.3.tar.gz
pip install 'requests>=2.25.1'
```

When the controller can reach GitHub:

```bash
ansible-galaxy collection install \
  https://github.com/PatchMon/PatchMon-ansible/releases/download/v2.0.3/patchmon-core-2.0.3.tar.gz
```

### From source

```bash
git clone https://github.com/PatchMon/PatchMon-ansible.git
cd PatchMon-ansible
ansible-galaxy collection build
ansible-galaxy collection install patchmon-core-*.tar.gz
pip install -r requirements.txt
```

Air-gapped steps and `enable_plugins` are in the [Install](docs/automator-guide.md#chapter-2-install) chapter.

## Inventory

Enable the plugin in `ansible.cfg` (`enable_plugins = patchmon.core.inventory`). Export `PATCHMON_SERVER_URL`, `PATCHMON_API_KEY`, and `PATCHMON_API_SECRET`, and omit `api_url`:

```yaml
---
plugin: patchmon.core.inventory
verify_ssl: true
```

Hostvars, groups, fleet plays, troubleshooting, and credentials are chapters of the [Automator guide](docs/automator-guide.md). Commented examples are in [`examples/`](examples/).

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).

## Authors

- Steve Libonati <stevelibonati@yahoo.com>
- Contributors welcome via [GitHub Issues](https://github.com/PatchMon/PatchMon-ansible/issues)

## Links

- [Automator guide](docs/automator-guide.md)
- [Developer guide](docs/developer-guide.md)
- [Documentation site](https://mrjoshuap.github.io/PatchMon-ansible/)
- [Examples index](examples/README.md)
- [Changelog](CHANGELOG.md)
- [Proposal to adopt patchmon.core 2.0](PROPOSAL.md)
- [PatchMon feedback drafts](PATCHMON-FEEDBACK.md)
- [Upvote: adopt patchmon.core 2.0](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5fj33qte04r3x9v6527stma)
- [This fork](https://github.com/mrjoshuap/PatchMon-ansible)
- [Upstream collection](https://github.com/PatchMon/PatchMon-ansible)
- [PatchMon](https://patchmon.net)
- [PatchMon docs](https://patchmon.net/docs)
- [PatchMon Integration API](https://patchmon.net/docs/patchmon-api-integrations-guide/integration-api-documentation)
- [Auto-Enrollment API](https://patchmon.net/docs/patchmon-api-integrations-guide/auto-enrolment-api-docs)
- [Feedback portal](https://feedback.patchmon.net/)
- [Report a PatchMon bug](https://github.com/PatchMon/PatchMon/issues)
- [Ask a PatchMon question](https://github.com/PatchMon/PatchMon/discussions)
- [Discord](https://patchmon.net/discord)

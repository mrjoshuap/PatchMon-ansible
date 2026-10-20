# Ansible Collection - patchmon.core

Dynamic inventory, modules, lookups, and roles for the [PatchMon](https://patchmon.net) Integration and Auto-Enrollment APIs.

## Description

The `inventory` plugin turns PatchMon hosts and host groups into a live Ansible inventory. With `include_stats: true` it also exposes reboot, update, security, OS, and reporting metadata as host variables and optional auto groups — so you can target fleets with `--limit patchmon_security_required` or Constructable expressions.

Companion content:

| Type | FQCN | Purpose |
|------|------|---------|
| Inventory | `patchmon.core.inventory` | List hosts / groups / stats hostvars |
| Module | `patchmon.core.host_info` | Aggregate `/info`, `/stats`, `/notes`, `/package_reports`, `/agent_queue`, … |
| Module | `patchmon.core.host_packages` | List packages (optionally updates only) |
| Module | `patchmon.core.host` | Enroll, update desired state, or delete |
| Module | `patchmon.core.host_action` | Queue a report, force an agent update, or regenerate agent credentials |
| Module | `patchmon.core.host_token` | Enrollment script / admin token CRUD |
| Lookup | `patchmon.core.host` | Ad-hoc per-host API lookups |
| Role | `patchmon.core.agent` | Install / start / stop / report / remove agent |
| Role | `patchmon.core.host` | Create, update desired state, or delete host entries |
| Role | `patchmon.core.report_health` | Fail unless the newest package report succeeded |

**Permissions matter.** Read plugins need Integration `host:get`. Creating hosts and installing agents need **Auto-Enrollment** credentials — not Integration Basic Auth. See **[docs/permissions.md](docs/permissions.md)**.

**Upgrading from 1.0.0** (`patchmon.dynamic_inventory`): this is a breaking change — install `patchmon.core` and update `plugin:` to `patchmon.core.inventory`. Step-by-step: **[docs/migrating_to_2.0.md](docs/migrating_to_2.0.md)**.

## Requirements

- **Ansible**: >= 2.15.0
- **Python**: 3.9+
- **Dependencies**: `requests >= 2.25.1`

## Installation

### Ansible Galaxy

```bash
ansible-galaxy collection install patchmon.core
```

### Offline / air-gapped (GitHub Release tarball)

Tagged releases publish `patchmon-core-<version>.tar.gz` as a release asset:

1. Download the tarball from the [Releases](https://github.com/PatchMon/PatchMon-ansible/releases) page (or your fork’s Releases).
2. Copy it to the target system.
3. Install:

```bash
ansible-galaxy collection install ./patchmon-core-2.0.0.tar.gz
pip install 'requests>=2.25.1'
```

Or install directly from a release URL when the controller can reach GitHub:

```bash
ansible-galaxy collection install \
  https://github.com/PatchMon/PatchMon-ansible/releases/download/v2.0.0/patchmon-core-2.0.0.tar.gz
```

### From source

```bash
git clone https://github.com/PatchMon/PatchMon-ansible.git
cd PatchMon-ansible
ansible-galaxy collection build
ansible-galaxy collection install patchmon-core-*.tar.gz
pip install -r requirements.txt
```

## Using the examples

Full walkthrough (inventory + playbooks, troubleshooting): **[examples/README.md](examples/README.md)**.

| Example | Purpose |
|---------|---------|
| [`examples/patchmon_inventory.yml`](examples/patchmon_inventory.yml) | Minimal / backward-compatible inventory |
| [`examples/patchmon_inventory_stats.yml`](examples/patchmon_inventory_stats.yml) | Stats inventory + optional Constructable |
| [`examples/playbooks/host_info.yml`](examples/playbooks/host_info.yml) | `host_info` over inventory hosts |
| [`examples/playbooks/pending_updates.yml`](examples/playbooks/pending_updates.yml) | `host_packages` (pending / security) |
| [`examples/playbooks/host_info_by_id.yml`](examples/playbooks/host_info_by_id.yml) | Modules by UUID (no dynamic inventory) |
| [`examples/playbooks/lookup_system.yml`](examples/playbooks/lookup_system.yml) | `host` lookup |
| [`examples/playbooks/host_desired_state.yml`](examples/playbooks/host_desired_state.yml) | Notes, groups, and `host_action` |

Quick path:

```bash
# After installing the collection and enabling the plugin (see examples/README.md)
cp examples/patchmon_inventory_stats.yml inventories/patchmon.yml
# Edit api_url; then:
export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
export PATCHMON_API_KEY='...'
export PATCHMON_API_SECRET='...'
ansible-inventory -i inventories/patchmon.yml --graph
ansible-playbook -i inventories/patchmon.yml examples/playbooks/pending_updates.yml \
  --limit patchmon_security_required
```

## Inventory configuration

Create an inventory file, or copy an example from [`examples/`](examples/) and edit `api_url`:

```yaml
---
plugin: patchmon.core.inventory
api_url: https://patchmon.example.com/api/v1/api/hosts
api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
verify_ssl: true
```

Canonical API URL: `https://<patchmon-host>/api/v1/api/hosts`  
(`api_url` may also be the instance root; the plugin appends `/api/v1/api/hosts`.)

### Configuration options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `plugin` | yes | — | Must be `patchmon.core.inventory` |
| `api_url` | yes | — | Hosts endpoint or instance root (`PATCHMON_API_URL`) |
| `api_key` | yes | — | Token Key (`PATCHMON_API_KEY`) |
| `api_secret` | yes | — | Token Secret (`PATCHMON_API_SECRET`) |
| `verify_ssl` | no | `true` | TLS verify (`PATCHMON_VERIFY_SSL`) |
| `timeout` | no | `30` | HTTP timeout (seconds) |
| `include_stats` | no | `false` | Request `?include=stats` and set `patchmon_*` hostvars |
| `hostgroup` | no | — | Filter by PatchMon group name(s) or UUID(s) |
| `auto_groups` | no | `true` | Derived groups when `include_stats` is true |
| `inventory_hostname_prefer` | no | `hostname` | `hostname` or `friendly_name` |
| `compose` / `groups` / `keyed_groups` | no | — | Ansible constructed inventory features |
| `cache` | no | `false` | Enable inventory caching |

### Data-rich inventory (`include_stats`)

```yaml
---
plugin: patchmon.core.inventory
api_url: https://patchmon.example.com/api/v1/api/hosts
include_stats: true
compose:
  patchmon_has_security_updates: patchmon_security_updates_count | int > 0
keyed_groups:
  - key: patchmon_update_state
    prefix: update_state
groups:
  reboot_and_security: patchmon_needs_reboot and patchmon_security_updates_count | int > 0
```

#### Host variables (with `include_stats`)

| Hostvar | Source |
|---------|--------|
| `ansible_host` / `patchmon_ip` | `ip` |
| `patchmon_id` | `id` |
| `patchmon_hostname` / `patchmon_friendly_name` | identity fields |
| `patchmon_os_type` / `patchmon_os_version` | OS |
| `patchmon_status` / `patchmon_effective_status` / `patchmon_reporting_state` | lifecycle / freshness |
| `patchmon_update_state` | `up_to_date`, `updates_pending`, `security_required` |
| `patchmon_needs_reboot` | boolean |
| `patchmon_updates_count` / `patchmon_security_updates_count` / `patchmon_total_packages` | package counts |
| `patchmon_last_update` | last agent report |

Unprefixed compose aliases `ip`, `hostname`, and `friendly_name` are also set for Constructable expressions. Prefer `patchmon_*` names in playbooks to avoid collisions with user variables.


#### Auto groups (when `include_stats` and `auto_groups`)

| Group | Condition |
|-------|-----------|
| `patchmon_needs_reboot` | `needs_reboot` |
| `patchmon_security_required` | `update_state == security_required` |
| `patchmon_updates_pending` | `update_state == updates_pending` |
| `patchmon_up_to_date` | `update_state == up_to_date` |
| `patchmon_stale` / `patchmon_overdue` | `reporting_state` |
| `patchmon_inactive` | `effective_status == inactive` |
| `patchmon_os_<os>` | sanitized `os_type` |

Plus every PatchMon `host_groups[].name` as an Ansible group.

```bash
ansible-playbook site.yml -i patchmon_inventory.yml --limit patchmon_security_required
ansible-playbook reboot.yml -i patchmon_inventory.yml --limit patchmon_needs_reboot
```

## Usage

```bash
# List inventory
ansible-inventory -i patchmon_inventory.yml --list

# Enable the plugin globally
# ansible.cfg:
# [inventory]
# enable_plugins = patchmon.core.inventory
```

### Modules

Call PatchMon from the control node (`delegate_to: localhost`). Prefer a stats inventory so `patchmon_id` is set, or pass the UUID with `-e patchmon_id=...`.

| Module | Purpose | Access |
|--------|---------|--------|
| `patchmon.core.host_info` | Aggregate host detail endpoints via `gather_subset` | Integration `host:get` |
| `patchmon.core.host_packages` | List packages; `updates_only: true` for pending updates | Integration `host:get` |
| `patchmon.core.host` | Enroll (`state=present`), update omitted-by-default fields, or delete (`state=absent`) | Auto-Enrollment / `host:patch` / `host:put` / `host:delete` |
| `patchmon.core.host_action` | `fetch_report`, `force_agent_update`, or `regenerate_credentials` | Integration `host:update` |
| `patchmon.core.host_token` | Fetch install script or manage enrollment tokens | Auto-Enrollment / admin JWT |

```yaml
- name: Gather PatchMon host details
  patchmon.core.host_info:
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    gather_subset: [info, stats, system]
  delegate_to: localhost
  register: pm_info

- name: List packages with updates
  patchmon.core.host_packages:
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    updates_only: true
  delegate_to: localhost
  register: pm_pkgs

- name: Show security updates
  ansible.builtin.debug:
    msg: "{{ item.name }}: {{ item.current_version }} -> {{ item.available_version }}"
  loop: "{{ pm_pkgs.packages | selectattr('is_security_update') | list }}"
  loop_control:
    label: "{{ item.name }}"
```

Runnable copies: [`examples/playbooks/`](examples/playbooks/).

### Roles and playbooks

| Role | Thin playbook | Purpose |
|------|---------------|---------|
| `patchmon.core.agent` | [`playbooks/agent.yml`](playbooks/agent.yml) | Install/start/stop/report/remove agent |
| `patchmon.core.host` | [`playbooks/host.yml`](playbooks/host.yml) | Enroll, update desired state, or delete host entries |

See each role’s README for variables and required credentials.

### Lookup

```yaml
- name: Fetch system details
  ansible.builtin.set_fact:
    patchmon_system: "{{ lookup('patchmon.core.host', patchmon_id, resource='system') }}"
```

`resource` may be `info`, `stats`, `system`, `network`, `integrations`, `packages`, or `notes`. For packages with updates only, pass `updates_only=true`. See [`examples/playbooks/lookup_system.yml`](examples/playbooks/lookup_system.yml).

## Authentication and permissions

**Read-only** (inventory, info, packages, lookup): Integration API HTTP Basic Auth with at least `host:get`. Create under **Settings → Integrations → API**.

**Provisioning** (create hosts, install agent): Auto-Enrollment key/secret under **Settings → Integrations → Auto-Enrollment**. There is no Integration `host:create` scope.

**Desired state** (friendly name, notes, auto-update, host-down alerts, groups): Integration `host:get` plus `host:patch` and/or `host:put`. Omitted fields are left unchanged. `groups: []` clears membership.

**Commands** (`host_action`): Integration `host:update`. A successful command is always changed. `regenerate_credentials` returns a one-time agent key and invalidates the previous one; set `no_log: true` on that task.

**Delete hosts**: Integration scope `host:delete`.

Full matrix and least-privilege guidance: **[docs/permissions.md](docs/permissions.md)**.

Prefer environment variables, Ansible Vault, or AAP credentials over plaintext secrets:

```bash
export PATCHMON_API_URL=https://patchmon.example.com/api/v1/api/hosts
export PATCHMON_API_KEY=...
export PATCHMON_API_SECRET=...
# Provisioning (separate from read-only tokens when possible):
export PATCHMON_SERVER_URL=https://patchmon.example.com
export PATCHMON_ENROLLMENT_KEY=...
export PATCHMON_ENROLLMENT_SECRET=...
```

## Compliance note

Host compliance status is **not** currently exposed on the scoped Integration API (`/api/v1/api/...`). Compliance routes live under `/api/v1/compliance/*` with session RBAC. This collection does not scrape session cookies. Tracking request: [PatchMon/PatchMon#1189](https://github.com/PatchMon/PatchMon/issues/1189). Once those fields land, a follow-up release will map `patchmon_compliance_*` hostvars and groups.

## Development

```bash
pip install -r requirements.txt pytest ansible-lint
pytest
ansible-lint examples/playbooks playbooks
```

Pull requests run the [CI](.github/workflows/ci.yml) workflow (pytest + ansible-lint).

### Cutting a release

1. Bump `galaxy.yml` `version`, update `CHANGELOG.md`, and merge to `main`.
2. Tag the release commit (tag must match `galaxy.yml`, with a `v` prefix):

```bash
git tag -a v2.0.0 -m "patchmon.core 2.0.0"
git push origin v2.0.0
```

3. The [Release collection](.github/workflows/release.yml) workflow runs tests, builds the collection tarball, and creates a GitHub Release with the `.tar.gz` attached for offline installs.

You can also run the workflow manually (**Actions → Release collection → Run workflow**) and supply an existing tag such as `v2.0.0`.

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).

## Authors

- Steve Libonati <stevelibonati@yahoo.com>
- Contributors welcome via [GitHub Issues](https://github.com/PatchMon/PatchMon-ansible/issues)

## Links

- Permissions: [docs/permissions.md](docs/permissions.md)
- Migrate from 1.x: [docs/migrating_to_2.0.md](docs/migrating_to_2.0.md)
- Examples guide: [examples/README.md](examples/README.md)
- Repository: https://github.com/PatchMon/PatchMon-ansible
- PatchMon Integration API docs: https://patchmon.net/docs/patchmon-api-integrations-guide/integration-api-documentation
- Auto-Enrollment API docs: https://patchmon.net/docs/patchmon-api-integrations-guide/auto-enrolment-api-docs
- Changelog: [CHANGELOG.md](CHANGELOG.md)

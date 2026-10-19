# Ansible Collection - patchmon.dynamic_inventory

Dynamic inventory, modules, and lookups for the [PatchMon](https://patchmon.net) Integration API.

## Description

The `dynamic_inventory` plugin turns PatchMon hosts and host groups into a live Ansible inventory. With `include_stats: true` it also exposes reboot, update, security, OS, and reporting metadata as host variables and optional auto groups — so you can target fleets with `--limit patchmon_security_required` or Constructable expressions.

Companion content:

| Type | Name | Purpose |
|------|------|---------|
| Inventory | `patchmon.dynamic_inventory` | List hosts / groups / stats hostvars |
| Module | `patchmon_host_info` | Aggregate `/info`, `/stats`, `/system`, … |
| Module | `patchmon_host_packages` | List packages (optionally updates only) |
| Lookup | `patchmon_host` | Ad-hoc per-host API lookups |

## Requirements

- **Ansible**: >= 2.15.0
- **Python**: 3.9+
- **Dependencies**: `requests >= 2.25.1`

## Installation

### Ansible Galaxy

```bash
ansible-galaxy collection install patchmon.dynamic_inventory
```

### Offline / air-gapped (GitHub Release tarball)

Tagged releases publish `patchmon-dynamic_inventory-<version>.tar.gz` as a release asset:

1. Download the tarball from the [Releases](https://github.com/PatchMon/PatchMon-ansible/releases) page (or your fork’s Releases).
2. Copy it to the target system.
3. Install:

```bash
ansible-galaxy collection install ./patchmon-dynamic_inventory-1.1.0.tar.gz
pip install 'requests>=2.25.1'
```

Or install directly from a release URL when the controller can reach GitHub:

```bash
ansible-galaxy collection install \
  https://github.com/PatchMon/PatchMon-ansible/releases/download/v1.1.0/patchmon-dynamic_inventory-1.1.0.tar.gz
```

### From source

```bash
git clone https://github.com/PatchMon/PatchMon-ansible.git
cd PatchMon-ansible
ansible-galaxy collection build
ansible-galaxy collection install patchmon-dynamic_inventory-*.tar.gz
pip install -r requirements.txt
```

## Inventory configuration

Create an inventory file (for example `patchmon_inventory.yml`):

```yaml
---
plugin: patchmon.dynamic_inventory
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
| `plugin` | yes | — | Must be `patchmon.dynamic_inventory` |
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

See also [`examples/patchmon_inventory.yml`](examples/patchmon_inventory.yml) and [`examples/patchmon_inventory_stats.yml`](examples/patchmon_inventory_stats.yml).

### Data-rich inventory (`include_stats`)

```yaml
---
plugin: patchmon.dynamic_inventory
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
# enable_plugins = patchmon.dynamic_inventory.dynamic_inventory
```

### Modules

```yaml
- name: Gather PatchMon host details
  patchmon.dynamic_inventory.patchmon_host_info:
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    gather_subset: [info, stats, system]
  delegate_to: localhost
  register: pm_info

- name: List packages with updates
  patchmon.dynamic_inventory.patchmon_host_packages:
    api_url: "{{ lookup('env', 'PATCHMON_API_URL') }}"
    api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
    api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
    host_id: "{{ patchmon_id }}"
    updates_only: true
  delegate_to: localhost
  register: pm_pkgs
```

### Lookup

```yaml
- name: Fetch system details
  ansible.builtin.debug:
    var: lookup('patchmon.dynamic_inventory.patchmon_host', patchmon_id, resource='system')
```

## Authentication

HTTP Basic Auth with a PatchMon Integration API credential (`host:get` scope minimum). Create credentials under **Settings → Integrations → API** in PatchMon.

Prefer environment variables or Ansible Vault over plaintext secrets in inventory files:

```bash
export PATCHMON_API_URL=https://patchmon.example.com/api/v1/api/hosts
export PATCHMON_API_KEY=...
export PATCHMON_API_SECRET=...
```

## Compliance note

Host compliance status is **not** currently exposed on the scoped Integration API (`/api/v1/api/...`). Compliance routes live under `/api/v1/compliance/*` with session RBAC. This collection does not scrape session cookies. Tracking request: [PatchMon/PatchMon#1189](https://github.com/PatchMon/PatchMon/issues/1189). Once those fields land, a follow-up release will map `patchmon_compliance_*` hostvars and groups.

## Development

```bash
pip install -r requirements.txt pytest
pytest
```

### Cutting a release

1. Bump `galaxy.yml` `version`, update `CHANGELOG.md`, and merge to `main`.
2. Tag the release commit (tag must match `galaxy.yml`, with a `v` prefix):

```bash
git tag -a v1.1.0 -m "patchmon.dynamic_inventory 1.1.0"
git push origin v1.1.0
```

3. The [Release collection](.github/workflows/release.yml) workflow runs tests, builds the collection tarball, and creates a GitHub Release with the `.tar.gz` attached for offline installs.

You can also run the workflow manually (**Actions → Release collection → Run workflow**) and supply an existing tag such as `v1.1.0`.

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).

## Authors

- Steve Libonati <stevelibonati@yahoo.com>
- Contributors welcome via [GitHub Issues](https://github.com/PatchMon/PatchMon-ansible/issues)

## Links

- Repository: https://github.com/PatchMon/PatchMon-ansible
- PatchMon Integration API docs: https://patchmon.net/docs/patchmon-api-integrations-guide/integration-api-documentation
- Changelog: [CHANGELOG.md](CHANGELOG.md)

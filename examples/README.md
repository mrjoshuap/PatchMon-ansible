# Examples

Ready-to-copy inventory YAML and playbooks for the `patchmon.core` collection.

### Inventory templates

Heavily commented: required options are active; everything else is commented with guidance.

| File | Use when |
|------|----------|
| [`patchmon_inventory.yml`](patchmon_inventory.yml) | Minimal / v1.0-compatible inventory (hosts, IPs, PatchMon groups only) |
| [`patchmon_inventory_stats.yml`](patchmon_inventory_stats.yml) | Data-rich inventory (`include_stats`) with auto groups and optional Constructable blocks |

Start with the minimal file if you only need PatchMon as a host/group source. Use the stats file when you want `--limit patchmon_needs_reboot`, security-update targeting, or custom `compose` / `keyed_groups`.

### Playbooks (modules & lookup)

| File | What it demonstrates |
|------|----------------------|
| [`playbooks/host_info.yml`](playbooks/host_info.yml) | `host_info` against inventory hosts (`patchmon_id`) |
| [`playbooks/pending_updates.yml`](playbooks/pending_updates.yml) | `host_packages` with `updates_only`, security vs other |
| [`playbooks/host_info_by_id.yml`](playbooks/host_info_by_id.yml) | Both modules on `localhost` with `-e patchmon_id=...` (no dynamic inventory) |
| [`playbooks/lookup_system.yml`](playbooks/lookup_system.yml) | `host` lookup for `/system` |

### Fleet lifecycle

These match the enroll, maintain, and retire flow in the [collection README](../README.md#enroll-maintain-and-retire). Run maintain, all-pending upgrades, and retire against a stats inventory. `Automated` and `No Reboot` must exist in PatchMon so `patchmon_automated` and `patchmon_no_reboot` are in the inventory. `maintain.yml` imports the three plays under it; keep those files in the same directory.

| File | What it does |
|------|----------------|
| [`playbooks/enroll.yml`](playbooks/enroll.yml) | Install the agent (`agent_state: present`). The host stays in the enrollment token's default group. |
| [`playbooks/maintain.yml`](playbooks/maintain.yml) | Refresh inventory, report health, security-only updates, reboot Automated one host at a time. |
| [`playbooks/report_health.yml`](playbooks/report_health.yml) | Fail a host whose newest package report is missing or not success. |
| [`playbooks/apply_security_updates.yml`](playbooks/apply_security_updates.yml) | `dnf` / `dnf5` security upgrades. Apt only with `-e patchmon_try_listed_security=true`. |
| [`playbooks/reboot_needed.yml`](playbooks/reboot_needed.yml) | Reboot `patchmon_automated` when `patchmon_needs_reboot` is true (`serial: 1`). |
| [`playbooks/apply_all_updates.yml`](playbooks/apply_all_updates.yml) | All pending packages on Automated and No Reboot. Not part of maintain. |
| [`playbooks/retire.yml`](playbooks/retire.yml) | Remove the agent, then delete the host when `patchmon_id` is set. Requires `--limit`. |

```bash
export PATCHMON_SERVER_URL='https://patchmon.example.com'
export PATCHMON_ENROLLMENT_KEY='...'
export PATCHMON_ENROLLMENT_SECRET='...'
ansible-playbook -i inventories/linux.yml \
  examples/playbooks/enroll.yml --limit web01.example.com

export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
export PATCHMON_API_KEY='...'
export PATCHMON_API_SECRET='...'
ansible-playbook -i inventories/patchmon.yml examples/playbooks/maintain.yml
ansible-playbook -i inventories/patchmon.yml examples/playbooks/apply_all_updates.yml
ansible-playbook -i inventories/patchmon.yml \
  examples/playbooks/retire.yml --limit web01.example.com
```

---

## Prerequisites

1. **Install the collection** (Galaxy, release tarball, or source) — see the [main README](../README.md#installation).
2. **Python dependency** on the control node (or EE):

   ```bash
   pip install 'requests>=2.25.1'
   ```

3. **PatchMon API credential** with at least `host:get` for these read-only examples.  
   Create under **Settings → Integrations → API** in PatchMon. You need the Token Key and Token Secret.  
   Provisioning (host create / agent install) needs a separate **Auto-Enrollment** token — see [docs/permissions.md](../docs/permissions.md).

4. **Enable the inventory plugin** (once per Ansible project), for example in `ansible.cfg`:

   ```ini
   [inventory]
   enable_plugins = patchmon.core.inventory
   ```

---

## Step-by-step: try an example

### 1. Copy an example into your project

```bash
mkdir -p inventories
cp examples/patchmon_inventory.yml inventories/patchmon.yml
# or:
cp examples/patchmon_inventory_stats.yml inventories/patchmon.yml
```

### 2. Point `api_url` at your PatchMon

Edit the copy and set:

```yaml
api_url: https://patchmon.example.com/api/v1/api/hosts
```

You may also use the instance root (`https://patchmon.example.com`); the plugin appends `/api/v1/api/hosts`.

Alternatively leave `api_url` as-is and export:

```bash
export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
```

### 3. Provide credentials (do not commit secrets)

Recommended:

```bash
export PATCHMON_API_KEY='<token key>'
export PATCHMON_API_SECRET='<token secret>'
# Optional:
# export PATCHMON_VERIFY_SSL=true
```

Other options (documented inside each example file):

- Uncomment `api_key` / `api_secret` with `lookup('env', ...)` or vaulted values
- Set `[patchmon]` keys in `ansible.cfg`

### 4. List the inventory

```bash
ansible-inventory -i inventories/patchmon.yml --list
ansible-inventory -i inventories/patchmon.yml --graph
```

Expect hosts under `patchmon_<slug>` groups (for example `patchmon_production`). A PatchMon name with a space, such as `No Reboot`, becomes `patchmon_no_reboot` when that slug is unique. With the **stats** example and `auto_groups: true`, also expect groups such as `patchmon_security_required` and `patchmon_needs_reboot`.

### 5. Run a simple check

```bash
# All hosts from PatchMon
ansible all -i inventories/patchmon.yml -m ping

# One PatchMon host group (Ansible name, not the raw PatchMon label)
ansible all -i inventories/patchmon.yml -m ping --limit patchmon_production
```

### 6. (Stats example) target derived groups

Only applies when using `patchmon_inventory_stats.yml` (or any inventory with `include_stats: true`):

```bash
ansible-playbook site.yml -i inventories/patchmon.yml --limit patchmon_security_required
ansible-playbook reboot.yml -i inventories/patchmon.yml --limit patchmon_needs_reboot
```

Inspect hostvars for one host:

```bash
ansible-inventory -i inventories/patchmon.yml --host web01.example.com
```

---

## Choosing between the two examples

```text
Need only hostname + IP + PatchMon groups?
  └─ patchmon_inventory.yml

Need reboot / updates / security / OS metadata or --limit on those?
  └─ patchmon_inventory_stats.yml
       └─ Uncomment compose / keyed_groups / groups as needed
```

| Capability | Minimal example | Stats example |
|------------|-----------------|---------------|
| Hosts + `ansible_host` | yes | yes |
| PatchMon `host_groups` → `patchmon_<slug>` groups | yes | yes |
| `patchmon_*` stats hostvars | no (default) | yes (`include_stats: true`; `stats_var_scope: targeting` drops telemetry) |
| Auto groups (`patchmon_needs_reboot`, …) | no | yes (unless you set `auto_groups: false`) |
| Commented Constructable samples | brief | full sections |

You can turn the minimal file into a stats inventory by setting `include_stats: true` (and optionally copying Constructable blocks from the stats example).

---

## Optional: filter by PatchMon host group

Both examples document `hostgroup`. Uncomment to ask the API for a subset (OR logic for lists):

```yaml
hostgroup: Production          # exact PatchMon name
hostgroup: "No Reboot"         # spaces must match the PatchMon name
# or:
hostgroup:
  - Production
  - Development
```

`No Reboot` and `No_Reboot` are different groups. A token with spaces already turned into `_` matches only when one PatchMon group sanitizes to it. If both exist, pass the group id or the exact name.

---

## Playbook examples (modules & lookup)

API modules always talk to PatchMon from the control node — use `delegate_to: localhost` (already set in the inventory-based playbooks) or `hosts: localhost`.

### Shared environment

```bash
export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
export PATCHMON_API_KEY='...'
export PATCHMON_API_SECRET='...'
# optional: export PATCHMON_VERIFY_SSL=false
```

### With PatchMon dynamic inventory

Use a stats inventory so each host has `patchmon_id`:

```bash
cp examples/patchmon_inventory_stats.yml inventories/patchmon.yml
# edit api_url, then:

ansible-playbook -i inventories/patchmon.yml \
  examples/playbooks/host_info.yml

ansible-playbook -i inventories/patchmon.yml \
  examples/playbooks/pending_updates.yml \
  --limit patchmon_security_required

ansible-playbook -i inventories/patchmon.yml \
  examples/playbooks/host_info.yml \
  --limit patchmon_needs_reboot
```

### Without dynamic inventory (UUID only)

```bash
ansible-playbook examples/playbooks/host_info_by_id.yml \
  -e patchmon_id=550e8400-e29b-41d4-a716-446655440000

ansible-playbook examples/playbooks/lookup_system.yml \
  -e patchmon_id=550e8400-e29b-41d4-a716-446655440000
```

### Module quick reference

| Module / lookup | Role |
|-----------------|------|
| `patchmon.core.host_info` | Aggregate `/info`, `/stats`, `/system`, `/network`, `/integrations` via `gather_subset` |
| `patchmon.core.host_packages` | List packages; `updates_only: true` for pending updates |
| `lookup('patchmon.core.host', id, resource='…')` | One-shot JSON for `info`, `stats`, `system`, `network`, `integrations`, `packages`, `notes` |

`host_info` return shape: `host.info`, `host.stats`, `host.system`, …  
`host_packages` return shape: `packages`, `total`, `security_updates_count`, `host`.

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Plugin not found / ignored | Collection installed? `enable_plugins` includes `patchmon.core.inventory`? Filename ends in `.yml` / `.yaml`? |
| Auth / HTTP 401 or 403 | `PATCHMON_API_KEY` / `PATCHMON_API_SECRET`; credential has `host:get` |
| Empty inventory | Hosts enrolled and active in PatchMon? `hostgroup` filter too narrow? |
| Redirect / empty body errors | Prefer URL **without** a trailing slash that 302s; use `.../api/v1/api/hosts` |
| TLS errors | Lab only: `verify_ssl: false` or `PATCHMON_VERIFY_SSL=false` |
| No `patchmon_needs_reboot` group | Using stats example? `include_stats: true` and `auto_groups: true`? |

Test the API outside Ansible:

```bash
curl -u "$PATCHMON_API_KEY:$PATCHMON_API_SECRET" \
  -H 'Accept: application/json' \
  "$PATCHMON_API_URL"
# With stats:
curl -u "$PATCHMON_API_KEY:$PATCHMON_API_SECRET" \
  -H 'Accept: application/json' \
  "${PATCHMON_API_URL}?include=stats"
```

---

## Related docs

- Collection overview, module/lookup reference: [../README.md](../README.md)
- PatchMon Integration API: https://patchmon.net/docs/patchmon-api-integrations-guide/integration-api-documentation

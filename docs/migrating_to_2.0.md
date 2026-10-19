# Migrating to patchmon.ansible 2.0.0

This is a **breaking** upgrade from `patchmon.dynamic_inventory` **1.0.0**.
There are no compatibility redirects — update installs and inventory YAML as below.

## 1. Install the new collection

```bash
ansible-galaxy collection install patchmon.ansible
# or from a release tarball:
# ansible-galaxy collection install ./patchmon-ansible-2.0.0.tar.gz
```

You can remove the old collection if it is still installed:

```bash
ansible-galaxy collection remove patchmon.dynamic_inventory
```

## 2. Update inventory configuration

| 1.0.0 | 2.0.0 |
|-------|-------|
| Collection `patchmon.dynamic_inventory` | Collection `patchmon.ansible` |
| `plugin: patchmon.dynamic_inventory.dynamic_inventory` | `plugin: patchmon.ansible.inventory` |

`ansible.cfg`:

```ini
[inventory]
enable_plugins = patchmon.ansible.inventory
```

Inventory file:

```yaml
---
plugin: patchmon.ansible.inventory
api_url: https://patchmon.example.com/api/v1/api/hosts
api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
verify_ssl: true
```

## 3. FQCN map (1.0.0 → 2.0.0)

1.0.0 shipped only the inventory plugin. Anything added later under interim names
should use the 2.0.0 FQCNs:

| Kind | Use in 2.0.0 |
|------|----------------|
| Inventory | `patchmon.ansible.inventory` |
| Module | `patchmon.ansible.host_info` |
| Module | `patchmon.ansible.host_packages` |
| Module | `patchmon.ansible.host` |
| Module | `patchmon.ansible.host_token` |
| Lookup | `lookup('patchmon.ansible.host', …)` |
| Role | `patchmon.ansible.agent` |
| Role | `patchmon.ansible.host` |

## 4. Credentials (new in 2.0.0 write paths)

| Use case | Credential |
|----------|------------|
| Inventory / info / packages / lookup | Integration API (`host:get`) |
| Enroll hosts / install agent | Auto-Enrollment key + secret |
| Delete hosts | Integration API (`host:delete`) |

See [permissions.md](permissions.md).

## 5. Smoke-test after migration

```bash
export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
export PATCHMON_API_KEY='...'
export PATCHMON_API_SECRET='...'

ansible-inventory -i inventories/patchmon.yml --graph
ansible-doc patchmon.ansible.inventory
ansible-doc patchmon.ansible.host_info
```

Copy-paste examples: [examples/README.md](../examples/README.md).

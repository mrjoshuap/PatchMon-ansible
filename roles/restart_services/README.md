# patchmon.core.restart_services

Restart configured services after patching when they are running.

Uses `patchmon_restart_services` (list), optional `patchmon_restart_services_map` (package → services), and optional `patchmon_restart_needrestart`. Only restarts services that are currently active. Skips needrestart when the binary is missing.

The play must set `become: true`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `restart_services_list` | `patchmon_restart_services`, else `[]` | Services to restart when running |
| `restart_services_map` | `patchmon_restart_services_map`, else `{}` | Package name → service list |
| `restart_services_needrestart` | `patchmon_restart_needrestart`, else `false` | Run needrestart when installed |
| `restart_services_upgraded_packages` | `[]` | Upgraded package names for the map |

## Example

```yaml
- name: Restart services after patching
  hosts: patchmon_automated:patchmon_no_reboot
  become: true
  vars:
    patchmon_restart_services:
      - nginx

  tasks:
    - name: Restart configured services
      ansible.builtin.import_role:
        name: patchmon.core.restart_services
```

Thin playbook: [examples/playbooks/restart_services.yml](../../examples/playbooks/restart_services.yml).

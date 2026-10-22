# patchmon.core.reboot_needed

Reboot a host when inventory hostvar `patchmon_needs_reboot` is true, then run a local agent report if the reboot changed the host.

Hosts in `patchmon_manual` or `patchmon_no_reboot` are skipped. This role does not call the PatchMon API and does not set a fact named `patchmon_needs_reboot`.

The play must set `become: true`, `gather_facts: false`, and `serial: 1`. Gathering facts can override `patchmon_needs_reboot` when a flat fact uses that name. Do not target the `patchmon_needs_reboot` group. That group exists only while a host matches.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `reboot_needed_timeout` | `600` | Seconds to wait for the host to come back |

## Example

```yaml
- name: Reboot automated hosts that PatchMon reports need a reboot
  hosts: patchmon_automated
  gather_facts: false
  become: true
  serial: 1

  tasks:
    - name: Reboot hosts that need a reboot
      ansible.builtin.import_role:
        name: patchmon.core.reboot_needed
```

Thin playbook: [examples/playbooks/reboot_needed.yml](../../examples/playbooks/reboot_needed.yml).

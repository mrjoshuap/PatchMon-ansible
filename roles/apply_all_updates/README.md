# patchmon.core.apply_all_updates

All pending package upgrades, then a local agent report.

Apt uses `apply_all_updates_apt_upgrade` (`safe` or `full`). `dnf`, `dnf5`, and `pacman` upgrade pending packages. A host also in `patchmon_manual` is skipped. Names in `patchmon_ignore_packages` are skipped. Optional lock wait uses `patchmon_pkg_force` with `patchmon_pkg_lock_timeout`. An eligible host whose package manager is not apt, dnf, dnf5, or pacman fails. The failure includes a subject and description to paste into a [PatchMon feedback](https://feedback.patchmon.net/) request. This role does not reboot and does not call the PatchMon API. The agent report is local.

The play must set `gather_facts: true` and `become: true`. Inventory knobs use host_vars, then group_vars, then play or extra vars, then role defaults.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `apply_all_updates_ignore_packages` | `patchmon_ignore_packages`, else `[]` | Package names to skip |
| `apply_all_updates_apt_upgrade` | `patchmon_apt_upgrade`, else `safe` | Apt upgrade mode (`safe` or `full`) |
| `apply_all_updates_lock_timeout` | `patchmon_pkg_lock_timeout`, else `0` | Seconds for lock wait / module `lock_timeout` |
| `apply_all_updates_force` | `patchmon_pkg_force`, else `false` | Wait for dpkg/dnf locks when timeout > 0 |

## Example

```yaml
- name: Apply all pending upgrades on Automated and No Reboot hosts
  hosts: patchmon_automated:patchmon_no_reboot
  gather_facts: true
  become: true

  tasks:
    - name: Apply all pending upgrades
      ansible.builtin.import_role:
        name: patchmon.core.apply_all_updates
```

Thin playbook: [examples/playbooks/apply_all_updates.yml](../../examples/playbooks/apply_all_updates.yml). `maintain.yml` imports that play when `-e apply_all_updates=true`.

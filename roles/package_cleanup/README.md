# patchmon.core.package_cleanup

Autoremove unused packages and optionally clean the package manager cache. Defaults to off.

Enable with `patchmon_cleanup_packages: true` or `package_cleanup_enabled: true`. Cache timing uses `patchmon_cleanup_cache` (`never`, `pre`, `post`, `both`). Skips `patchmon_manual`. Supports apt, dnf, dnf5, and pacman. After a change, optionally reports via `patchmon.core.agent`.

The play must set `gather_facts: true` and `become: true`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `package_cleanup_enabled` | `patchmon_cleanup_packages`, else `false` | Run autoremove |
| `package_cleanup_cache` | `patchmon_cleanup_cache`, else `never` | Cache clean timing |
| `package_cleanup_report` | `true` | Agent report after a change |

## Example

```yaml
- name: Clean unused packages on PatchMon hosts
  hosts: patchmon_automated:patchmon_no_reboot
  gather_facts: true
  become: true
  vars:
    patchmon_cleanup_packages: true
    patchmon_cleanup_cache: post

  tasks:
    - name: Autoremove unused packages
      ansible.builtin.import_role:
        name: patchmon.core.package_cleanup
```

Thin playbook: [examples/playbooks/package_cleanup.yml](../../examples/playbooks/package_cleanup.yml).

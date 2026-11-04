# patchmon.core.kernel_cleanup

Remove old kernels after checking `/boot` free space. Defaults to off.

Enable with `patchmon_kernel_cleanup: true`. Keeps the newest `patchmon_kernel_keep` kernels (default 2) and never removes the running kernel. Warns when free space is below `patchmon_boot_min_free_mb`. Supports apt, dnf, and dnf5. Skips `patchmon_manual`.

The play must set `gather_facts: true` and `become: true`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `kernel_cleanup_enabled` | `patchmon_kernel_cleanup`, else `false` | Run kernel cleanup |
| `kernel_cleanup_keep` | `patchmon_kernel_keep`, else `2` | Newest kernels to keep |
| `kernel_cleanup_boot_min_free_mb` | `patchmon_boot_min_free_mb`, else `256` | Free-space warning floor (MiB) |
| `kernel_cleanup_report` | `true` | Agent report after a change |

## Example

```yaml
- name: Clean old kernels
  hosts: patchmon_automated:patchmon_no_reboot
  gather_facts: true
  become: true
  vars:
    patchmon_kernel_cleanup: true

  tasks:
    - name: Remove old kernels
      ansible.builtin.import_role:
        name: patchmon.core.kernel_cleanup
```

Thin playbook: [examples/playbooks/kernel_cleanup.yml](../../examples/playbooks/kernel_cleanup.yml).

# patchmon.core.apply_all_updates

All pending package upgrades, then a local agent report.

Apt uses a safe upgrade. `dnf` and `dnf5` use `state: latest`. A host also in `patchmon_manual` is skipped. An eligible host whose package manager is not apt, dnf, or dnf5 fails. The failure includes a subject and description to paste into a [PatchMon feedback](https://feedback.patchmon.net/) request. This role does not reboot and does not call the PatchMon API. The agent report is local.

The play must set `gather_facts: true` and `become: true`. This role has no role variables.

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

Thin playbook: [examples/playbooks/apply_all_updates.yml](../../examples/playbooks/apply_all_updates.yml). `maintain.yml` does not import that play.

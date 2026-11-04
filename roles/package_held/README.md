# patchmon.core.package_held

Detect APT holds and DNF versionlocks locally. Sets facts `package_held_packages` and `patchmon_held_packages` and prints them. Does not call PatchMon; dashboard held indicators need a server API.

The play must set `gather_facts: true` and `become: true`.

## Example

```yaml
- name: Show held packages
  hosts: all
  gather_facts: true
  become: true

  tasks:
    - name: Detect held packages
      ansible.builtin.import_role:
        name: patchmon.core.package_held
```

Thin playbook: [examples/playbooks/package_held.yml](../../examples/playbooks/package_held.yml).

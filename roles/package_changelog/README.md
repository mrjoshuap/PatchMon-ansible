# patchmon.core.package_changelog

Fetch a package changelog from the local package manager (`apt-get changelog`, `dnf changelog`, or `pacman -Qi`). Sets `package_changelog_text` and `patchmon_package_changelog_text`. Does not call PatchMon; UI changelogs need a server API.

The play must set `gather_facts: true` and `become: true`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `package_changelog_name` | `patchmon_package_changelog` | Package name (required) |

## Example

```yaml
- name: Show openssl changelog
  hosts: all
  gather_facts: true
  become: true
  vars:
    patchmon_package_changelog: openssl

  tasks:
    - name: Fetch package changelog
      ansible.builtin.import_role:
        name: patchmon.core.package_changelog
```

Thin playbook: [examples/playbooks/package_changelog.yml](../../examples/playbooks/package_changelog.yml).

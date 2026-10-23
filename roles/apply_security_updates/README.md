# patchmon.core.apply_security_updates

Security-only package updates for hosts PatchMon reports as needing them, then a local agent report.

`dnf` and `dnf5` use `security: true` when inventory hostvar `patchmon_update_state` is `security_required`, or when `patchmon_security_updates_count` is greater than zero. A host also in `patchmon_manual` is skipped. Apt has no security-only flag, so apt hosts are unchanged unless `apply_security_updates_try_listed` is true. That path calls `patchmon.core.host_packages` (`updates_only: true`, Integration `host:get`) and upgrades names where `is_security_update` is true. Any other package manager fails the eligible host. The failure includes a subject and description to paste into a [PatchMon feedback](https://feedback.patchmon.net/) request. This role does not reboot.

The play must set `gather_facts: true` and `become: true`. Do not put `patchmon_security_required` in `hosts:`. That group exists only while a host matches. `patchmon_update_state` and `patchmon_security_updates_count` stay inventory hostvars.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `apply_security_updates_try_listed` | `patchmon_try_listed_security`, else `false` | Upgrade apt packages PatchMon marks as security updates |
| `apply_security_updates_host_id` | `patchmon_id` | Host UUID for the apt package list |
| `apply_security_updates_api_url` | derived from `PATCHMON_SERVER_URL` | Integration hosts URL for the apt package list. `PATCHMON_API_URL` overrides it and is discouraged |
| `apply_security_updates_api_key` / `apply_security_updates_api_secret` | env | Integration Basic Auth for the apt package list |
| `apply_security_updates_verify_ssl` | `PATCHMON_VERIFY_SSL`, else `true` | TLS verify for the apt package list |
| `apply_security_updates_timeout` | `30` | HTTP timeout in seconds for the apt package list |

API credentials are checked only when the apt opt-in runs. `dnf` and `dnf5` do not call PatchMon. The agent report is local.

## Example

```yaml
- name: Apply security updates for PatchMon security_required hosts
  hosts: patchmon_automated:patchmon_no_reboot
  gather_facts: true
  become: true

  tasks:
    - name: Apply security updates
      ansible.builtin.import_role:
        name: patchmon.core.apply_security_updates
```

Pass `-e patchmon_try_listed_security=true` or `-e apply_security_updates_try_listed=true` to upgrade listed apt security packages. Thin playbook: [examples/playbooks/apply_security_updates.yml](../../examples/playbooks/apply_security_updates.yml).

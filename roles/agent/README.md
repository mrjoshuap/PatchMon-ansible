# patchmon.core.agent

Install, start, stop, report, or remove the PatchMon agent on managed Linux hosts.

When facts are present and `ansible_os_family` is `Windows`, the role fails before the POSIX enrollment script. The failure includes a subject and description to paste into a [PatchMon feedback](https://feedback.patchmon.net/) request. PatchMon's Windows installer is PowerShell. This role only runs `direct-host` or `proxmox-lxc`.

On FreeBSD, `agent_state` of `present`, `started`, or `stopped` can run the enrollment script, then fails before the service task. FreeBSD registers `/usr/local/etc/rc.d/patchmon_agent`. The role looks for `patchmon-agent`. That failure also includes a feedback draft. `report` and `absent` do not use that check. Plays that do not gather facts skip both OS checks.

If the enrollment script fails and its output reports an unsupported operating system, package manager, or architecture, the role fails with a feedback draft. That message does not include the script output, which can contain the enrollment URL. Other script failures still print the return code and stderr.

## Required API / credentials

| Operation | Credential | Notes |
|-----------|------------|-------|
| Install (`agent_state=present`) | Auto-Enrollment key + secret | Not an Integration API token. Create under **Settings → Integrations → Auto-Enrollment**. |
| Start / stop / report / absent | None (local host) | Uses `systemctl` / agent binary on the target. |

See [Credentials](../../docs/automator-guide.md#chapter-3-credentials).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `agent_state` | `present` | `present`, `started`, `stopped`, `absent`, `report` |
| `agent_server_url` | derived from `PATCHMON_SERVER_URL` | Auto-enrollment URL (`/api/v1/auto-enrollment`). `PATCHMON_ENROLLMENT_URL` overrides it and is discouraged. `PATCHMON_API_URL` is a last resort |
| `agent_enrollment_key` / `agent_enrollment_secret` | env | Auto-enrollment credentials |
| `agent_script_type` | `direct-host` | Or `proxmox-lxc` |
| `agent_force_new_host` | `false` | Sets `FORCE_NEW_HOST` for the installer |
| `agent_script_path` | `/tmp/patchmon-enroll.sh` | Staging path for the enrollment script on the target |
| `agent_script_controller_path` | `/tmp/patchmon-enroll-<host>.sh` | Controller path written by `host_token` (`dest`) |
| `agent_keep_failed_script` | `false` | On failure, copy script to `agent_failed_script_path` (contains secrets) |
| `agent_failed_script_path` | `/var/tmp/patchmon-enroll-failed-<host>.sh` | Durable path when `agent_keep_failed_script` is true |
| `agent_report` | `false` | Run `patchmon-agent report` after present |

## Example

```yaml
- name: Ensure PatchMon agent is installed
  hosts: linux
  become: true
  roles:
    - role: patchmon.core.agent
      vars:
        agent_state: present
        agent_server_url: https://patchmon.example.com
        agent_enrollment_key: "{{ vault_enrollment_key }}"
        agent_enrollment_secret: "{{ vault_enrollment_secret }}"
```

Thin playbook: [playbooks/agent.yml](../../playbooks/agent.yml).

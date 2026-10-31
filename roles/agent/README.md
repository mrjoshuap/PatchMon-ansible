# patchmon.core.agent

Install, start, stop, report, or remove the PatchMon agent on managed Linux hosts.

Windows support is experimental and limited to `started`, `stopped`, and `report` for an already-installed agent. Gather OS facts for Windows routing; without OS facts, the role retains its existing POSIX behavior. Windows installation (`present`) and removal (`absent`) fail before changing the host. See [Windows setup](../../docs/automator-guide.md#windows-agent-management) for prerequisites and an example.

On FreeBSD, `agent_state` of `present`, `started`, or `stopped` can run the enrollment script, then fails before the service task. FreeBSD registers `/usr/local/etc/rc.d/patchmon_agent`. The role looks for `patchmon-agent`. That failure also includes a feedback draft. `report` and `absent` do not use that check. Plays without OS facts skip the FreeBSD check.

If the enrollment script fails and its output reports an unsupported operating system, package manager, or architecture, the role fails with a feedback draft. That message does not include the script output, which can contain the enrollment URL. Other script failures still print the return code and stderr.

## Required API / credentials

| Operation | Credential | Notes |
|-----------|------------|-------|
| Linux install (`agent_state=present`) | Auto-Enrollment key + secret | Not an Integration API token. Create under **Settings → Integrations → Auto-Enrollment**. |
| Start / stop / report / absent | None (local host) | Uses the service manager / agent binary on the target; Windows supports start, stop, and report only. |

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

Windows defaults: `agent_service_name=PatchMonAgent`, `agent_binary_path=C:\Program Files\PatchMon\patchmon-agent.exe`, and `agent_config_dir=C:\ProgramData\PatchMon`. Override these for an existing custom installation. Reports explicitly use `<agent_config_dir>\config.yml`. Starting the service also sets automatic startup; stopping it preserves its startup mode.

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

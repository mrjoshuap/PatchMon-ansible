# patchmon.core.agent

Install, start, stop, report, or remove the PatchMon agent on managed Linux and Windows hosts.

Gather OS facts for Windows routing; without OS facts, the role retains its existing POSIX behavior. See [Windows agent management](../../docs/automator-guide.md#windows-agent-management) for connection prerequisites and examples.

On FreeBSD, `agent_state` of `present`, `started`, or `stopped` can run the enrollment script, then fails before the service task. FreeBSD registers `/usr/local/etc/rc.d/patchmon_agent`. The role looks for `patchmon-agent`. That failure also includes a feedback draft. `report` and `absent` do not use that check. Plays without OS facts skip the FreeBSD check.

If the Linux enrollment script fails and its output reports an unsupported operating system, package manager, or architecture, the role fails with a feedback draft. That message does not include the script output, which can contain the enrollment URL. Other script failures still print the return code and stderr.

## Check mode

With `agent_state: present`, `--check` validates required inputs and prints an installation preview. It does not fetch, stage, or execute the installer, manage the service, or send the optional post-install report. This works even when no installer file or agent service exists. It reports no predicted changes because the external script's behavior cannot be determined without executing it; a successful preview does not verify API credentials or guarantee installation success. Other agent states retain their existing check-mode behavior.

## Required API / credentials

| Operation | Credential | Notes |
|-----------|------------|-------|
| Install (`agent_state=present`) | Auto-Enrollment key + secret | Not an Integration API token. Create under **Settings → Integrations → Auto-Enrollment**. |
| Windows remove (`absent`) | Server URL only | Downloads `GET /api/v1/hosts/remove?os=windows` (no auth). Prefer `PATCHMON_SERVER_URL`. |
| Start / stop / report / Linux absent | None (local host) | Uses the service manager / agent binary on the target. |

Linux install uses `GET /api/v1/auto-enrollment/script`. Windows install enrolls then uses `GET /api/v1/hosts/install?os=windows` (same flow as PatchMon's Intune scripts). Neither path deletes the PatchMon host record on `absent`.

See [Credentials](../../docs/automator-guide.md#chapter-3-credentials).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `agent_state` | `present` | `present`, `started`, `stopped`, `absent`, `report` |
| `agent_server_url` | derived from `PATCHMON_SERVER_URL` | Auto-enrollment / instance URL. `PATCHMON_ENROLLMENT_URL` overrides it and is discouraged. `PATCHMON_API_URL` is a last resort |
| `agent_enrollment_key` / `agent_enrollment_secret` | env | Auto-enrollment credentials |
| `agent_script_type` | `direct-host` | Linux only: `direct-host` or `proxmox-lxc` |
| `agent_force_install` | `false` | Pass `force=true` to the install endpoint; on Windows also re-runs install when the service is already running |
| `agent_force_new_host` | `false` | Linux: `FORCE_NEW_HOST`. Windows: skip already-running short circuit |
| `agent_script_path` | `/tmp/patchmon-enroll.sh` | Staging path on the target (Windows override in `vars/Windows.yml`) |
| `agent_script_controller_path` | `/tmp/patchmon-enroll-<host>.sh` | Controller path written by `host_token` / `host_agent_script` |
| `agent_keep_failed_script` | `false` | On failure, copy script to `agent_failed_script_path` (contains secrets) |
| `agent_failed_script_path` | `/var/tmp/patchmon-enroll-failed-<host>.sh` | Durable path when `agent_keep_failed_script` is true |
| `agent_friendly_name` | gathered hostname | Windows enroll friendly name |
| `agent_host_id` | `""` | Optional Windows re-enrollment host UUID |
| `agent_report` | `false` | Run agent report after present |

Windows defaults (`vars/Windows.yml`): `agent_service_name=PatchMonAgent`, `agent_binary_path=C:\Program Files\PatchMon\patchmon-agent.exe`, and `agent_config_dir=C:\ProgramData\PatchMon`. Reports use `<agent_config_dir>\config.yml`. Starting the service also sets automatic startup; stopping it preserves its startup mode.

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

Windows example: [examples/playbooks/windows_agent.yml](../../examples/playbooks/windows_agent.yml). Thin playbook: [playbooks/agent.yml](../../playbooks/agent.yml).

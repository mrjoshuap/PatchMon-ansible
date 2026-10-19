# patchmon.core.agent

Install, start, stop, report, or remove the PatchMon agent on managed Linux hosts.

## Required API / credentials

| Operation | Credential | Notes |
|-----------|------------|-------|
| Install (`agent_state=present`) | Auto-Enrollment key + secret | Not an Integration API token. Create under **Settings → Integrations → Auto-Enrollment**. |
| Start / stop / report / absent | None (local host) | Uses `systemctl` / agent binary on the target. |

See [docs/permissions.md](../../docs/permissions.md).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `agent_state` | `present` | `present`, `started`, `stopped`, `absent`, `report` |
| `agent_server_url` | env `PATCHMON_SERVER_URL` / `PATCHMON_API_URL` | PatchMon instance root |
| `agent_enrollment_key` / `agent_enrollment_secret` | env | Auto-enrollment credentials |
| `agent_script_type` | `direct-host` | Or `proxmox-lxc` |
| `agent_force_new_host` | `false` | Sets `FORCE_NEW_HOST` for the installer |
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

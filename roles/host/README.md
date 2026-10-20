# patchmon.core.host

Create (auto-enroll) or delete PatchMon host entries.

## WARNING — permissions and blast radius

| `host_state` | Credential | Scope / permission | Effect |
|--------------|------------|--------------------|--------|
| `present` | Auto-Enrollment key + secret | Enrollment token | Creates a host row and returns one-time `api_id` / `api_key` |
| `present` with managed fields | Integration API key + secret | `host:get` plus `host:patch` and/or `host:put` | Updates only the fields you set. Enrollment is optional when `host_id` is set |
| `absent` | Integration API key + secret | `host:delete` | **Permanently deletes** the host and related data |

Integration tokens with only `host:get` **cannot** create hosts. There is no `host:create` Integration scope; use Auto-Enrollment.

Prefer separate credentials for read-only inventory vs provisioning. Never commit secrets. See [docs/permissions.md](../../docs/permissions.md).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `host_state` | `present` | `present` or `absent` |
| `host_friendly_name` | `inventory_hostname` | Display name for enrollment |
| `host_enrollment_key` / `host_enrollment_secret` | env | Auto-enrollment token |
| `host_api_key` / `host_api_secret` | env | Integration API (list + delete) |
| `host_enroll_agent` | `false` | After present, run `patchmon.core.agent` |
| `host_fetch_script` | `false` | Fetch installer script via `host_token` (`dest` is required) |
| `host_script_controller_path` | `/tmp/patchmon-enroll-<hostname>.sh` | Controller file for the fetched script (mode `0700`; contains secrets) |
| `host_friendly_name_update` | unset | Desired friendly name. Unset leaves the current name unchanged |
| `host_notes` | unset | Desired notes. `""` clears notes. Unset leaves notes unchanged |
| `host_auto_update` | unset | `true` or `false`. Unset leaves the flag unchanged |
| `host_host_down_alerts` | unset | `true` or `false` override. Unset leaves the current setting unchanged |
| `host_groups` | unset | List of group names or UUIDs. Replaces membership. `[]` clears it. Unset leaves groups unchanged |

Do not default `host_groups` to `[]` or `host_notes` to `""` in inventory. Those values are applied. Commands such as regenerate-credentials stay on `patchmon.core.host_action` and are not part of this role.

## Example

```yaml
- name: Enroll host in PatchMon
  hosts: localhost
  gather_facts: false
  roles:
    - role: patchmon.core.host
      vars:
        host_state: present
        host_server_url: https://patchmon.example.com
        host_friendly_name: web-01
        host_enrollment_key: "{{ vault_enrollment_key }}"
        host_enrollment_secret: "{{ vault_enrollment_secret }}"
```

Thin playbook: [playbooks/host.yml](../../playbooks/host.yml).

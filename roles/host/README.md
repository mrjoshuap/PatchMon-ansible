# patchmon.core.host

Create (auto-enroll) or delete PatchMon host entries.

## WARNING — permissions and blast radius

| `host_state` | Credential | Scope / permission | Effect |
|--------------|------------|--------------------|--------|
| `present` | Auto-Enrollment key + secret | Enrollment token | Creates a host row and returns one-time `api_id` / `api_key` |
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
| `host_fetch_script` | `false` | Fetch installer script via `host_token` |

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

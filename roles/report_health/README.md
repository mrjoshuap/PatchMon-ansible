# patchmon.core.report_health

Read-only check of the newest PatchMon package report. Fails the host when PatchMon has no reports or the newest report `status` is not `success`.

Uses Integration scope `host:get` (`GET /hosts/:id/package_reports`). Does not install packages or talk to the agent.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `report_health_host_id` | `patchmon_id` | PatchMon host UUID |
| `report_health_api_url` | `PATCHMON_API_URL` | Integration API URL |
| `report_health_api_key` / `report_health_api_secret` | env | Integration Basic Auth |
| `report_health_limit` | `10` | `limit` query parameter |

Run this before a patch job so a host whose last report failed is not upgraded from stale inventory stats.

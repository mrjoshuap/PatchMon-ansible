# PatchMon feedback

Short requests for the [feedback portal](https://feedback.patchmon.net/). Each block under a heading is meant to be pasted as one post. The compliance item is already posted.

Some role and module failures print their own subject and description. Paste those two lines from the job output. The requests below stay here because the collection does not call those routes.

## Update host fields on the Integration API

```text
PATCH friendly-name, notes, auto-update, and host-down alerts exist only for a signed-in user under /api/v1/hosts/{id}/.... GET notes already exists on the Integration API.

Please add the same PATCH routes under /api/v1/api/hosts/{id}/... with scope host:patch.
```

## Replace host group membership on the Integration API

```text
Replacing a host's groups is a session route today (PUT /api/v1/hosts/{id}/groups, can_manage_hosts). GET /api/v1/host-groups is also session-only. This extends https://github.com/PatchMon/PatchMon/issues/595.

Please add GET /api/v1/api/host-groups with scope host:get, and PUT /api/v1/api/hosts/{id}/groups with scope host:put that replaces the full set.
```

## Run host commands on the Integration API

```text
POST fetch-report, force-agent-update, and regenerate-credentials exist only for a signed-in user under /api/v1/hosts/{id}/....

Please add those three routes under /api/v1/api/hosts/{id}/... with scope host:update. regenerate-credentials must still return the new key once.
```

## Return host_id on enrollment machine_id_match

```text
POST /api/v1/auto-enrollment/enroll returns 409 machine_id_match with friendly_name and without host_id. The other 409 codes include host_id.

Please include host_id on machine_id_match as well.
```

## Document session-only routes in OpenAPI

```text
/api/v1/openapi.json covers scoped reads and auto-enrollment. It does not document the session host writes (field PATCH, group replacement, fetch-report, force-agent-update, regenerate-credentials). Clients then guess /api/v1/api/... paths that 404.

Please document those session routes, and mark which ones are not on the Integration API.
```

## Compliance summary on the Integration API

Already posted: [Expose compliance summary on the Integration API](https://feedback.patchmon.net/b/feature-requests/posts/post_01m5aw69zbe04r3hm0efeedbxj).

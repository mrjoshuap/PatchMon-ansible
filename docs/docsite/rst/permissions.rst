.. _ansible_collections.patchmon.core.docsite.permissions:

PatchMon API permissions for this collection
============================================

PatchMon uses different credential types for different operations. Using the wrong type produces HTTP 401/403 errors that look like a bad password when the real issue is scope or auth model.

Credential types
----------------

.. list-table::
   :header-rows: 1
   :widths: 18 28 24 30

   * - Type
     - Auth
     - Where created
     - Used for
   * - Integration API
     - HTTP Basic (``api_key``:``api_secret``)
     - Settings → Integrations → API
     - Inventory, ``host_info``, ``host_packages``, lookup, host desired state, host commands, host delete
   * - Auto-Enrollment
     - ``X-Auto-Enrollment-Key`` / ``X-Auto-Enrollment-Secret`` (or script query params)
     - Settings → Integrations → Auto-Enrollment
     - Create host entries, download install script, ``agent`` / ``host`` roles
   * - Admin session JWT
     - ``Authorization: Bearer …``
     - Logged-in admin session
     - Create/delete enrollment tokens (``host_token`` state ``present``/``absent``)
   * - Per-host agent creds
     - ``X-API-ID`` / ``X-API-KEY``
     - Returned once at enrollment
     - Agent communication (not used directly by most collection modules)

Integration API credentials are not the same as UI session RBAC. Compliance routes under ``/api/v1/compliance/*`` remain session-scoped; see `Expose compliance summary on the Integration API <https://feedback.patchmon.net/b/feature-requests/posts/post_01m5aw69zbe04r3hm0efeedbxj>`_.

Integration API scopes
----------------------

Scopes are explicit. ``get`` does not imply ``delete``.

.. list-table::
   :header-rows: 1
   :widths: 16 84

   * - Scope
     - Capabilities in this collection
   * - ``host:get``
     - Inventory plugin, ``host_info`` (including ``notes``, ``package_reports``, ``agent_queue``), ``host_packages``, ``lookup('patchmon.core.host')``, ``report_health`` role, existence checks before enroll, compares before ``host:patch`` / ``host:put``, ``GET /api/v1/api/host-groups``
   * - ``host:patch``
     - Partial updates on ``patchmon.core.host``: ``friendly_name_update``, ``notes``, ``auto_update``, ``host_down_alerts``
   * - ``host:put``
     - Replace host group membership (``groups`` on ``patchmon.core.host``). An empty list clears groups
   * - ``host:update``
     - ``patchmon.core.host_action``: ``fetch_report``, ``force_agent_update``, ``regenerate_credentials``
   * - ``host:delete``
     - ``patchmon.core.host`` with ``state=absent``, ``roles/host`` when ``host_state=absent``

``get`` does not imply ``patch``, ``put``, ``update``, or ``delete``. Those write scopes are not synonyms:

- ``host:patch`` changes scalar fields.
- ``host:put`` replaces the group set.
- ``host:update`` runs commands that are not convergent.

There is no Integration ``host:create`` scope. Host creation uses the Auto-Enrollment API.

Write routes this collection calls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 12 52 20

   * - Method
     - Path
     - Scope
   * - PATCH
     - ``/api/v1/api/hosts/{id}/friendly-name``
     - ``host:patch``
   * - PATCH
     - ``/api/v1/api/hosts/{id}/notes``
     - ``host:patch``
   * - PATCH
     - ``/api/v1/api/hosts/{id}/auto-update``
     - ``host:patch``
   * - PATCH
     - ``/api/v1/api/hosts/{id}/host-down-alerts``
     - ``host:patch``
   * - PUT
     - ``/api/v1/api/hosts/{id}/groups``
     - ``host:put``
   * - GET
     - ``/api/v1/api/host-groups``
     - ``host:get``
   * - POST
     - ``/api/v1/api/hosts/{id}/fetch-report``
     - ``host:update``
   * - POST
     - ``/api/v1/api/hosts/{id}/force-agent-update``
     - ``host:update``
   * - POST
     - ``/api/v1/api/hosts/{id}/regenerate-credentials``
     - ``host:update``

``GET /hosts/{id}/info`` must include ``friendly_name``, ``auto_update``, ``host_down_alerts_enabled``, and ``host_groups`` so compares can skip unchanged fields. A server that only implements ``host:get`` and ``host:delete`` returns HTTP 404 for the write paths and for ``GET /host-groups``.

Auto-Enrollment
---------------

.. list-table::
   :header-rows: 1
   :widths: 40 24 36

   * - Capability
     - Auth
     - Consumers
   * - Enroll host (``POST …/auto-enrollment/enroll``)
     - Enrollment key/secret
     - Module ``host`` (``state=present``), role ``host``
   * - Fetch install script (``GET …/auto-enrollment/script``)
     - Enrollment key/secret
     - Module ``host_token`` (``state=script``), role ``agent``
   * - Create/delete enrollment tokens
     - Admin JWT (Manage Settings)
     - Module ``host_token`` (``state=present`` / ``absent``)

Enrollment returns a one-time host ``api_key``. Treat it as a secret (``no_log`` on tasks).

Least-privilege guidance
------------------------

1. **Read-only automation** (inventory, reporting playbooks): Integration token with only ``host:get``.
2. **Provisioning** (create hosts / install agents): dedicated Auto-Enrollment token with IP allow lists and daily host limits where possible.
3. **Decommission** (delete hosts): separate Integration token with ``host:get`` + ``host:delete``, or a tightly controlled job; never share delete tokens with inventory-only projects.
4. **Desired state** (name, notes, auto-update, host-down alerts): Integration token with ``host:get`` + ``host:patch``. Group membership jobs add ``host:put`` and still omit ``host:delete``.
5. **Commands** (``host_action``): a separate Integration token with ``host:update``. Do not combine it with ``host:delete``. ``regenerate_credentials`` invalidates the current agent key.
6. **Token minting** (create enrollment tokens from Ansible): admin JWT only on trusted Controllers; prefer creating tokens in the UI and injecting key/secret via Vault / AAP credentials.
7. Store secrets in Ansible Vault, AAP Credential, or environment variables — never commit plaintext keys.
8. Keep ``verify_ssl: true`` outside lab environments.

HTTP status quick reference
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Status
     - Likely cause
   * - 401
     - Wrong key/secret, or using Integration creds on Auto-Enrollment (or the reverse)
   * - 403
     - Missing scope (``host:get`` / ``host:patch`` / ``host:put`` / ``host:update`` / ``host:delete``) or enrollment IP not allowed
   * - 404
     - Unknown host, or the server does not implement that write route yet
   * - 409
     - Host already enrolled / ``machine_id`` conflict (often safe to treat as already present)
   * - 429
     - Enrollment rate limit or re-enroll cooldown

Per-plugin summary
------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Plugin / role
     - Minimum access
   * - ``patchmon.core.inventory``
     - Integration ``host:get``
   * - ``patchmon.core.host_info`` / ``host_packages`` / lookup ``host``
     - Integration ``host:get``
   * - ``patchmon.core.report_health``
     - Integration ``host:get`` (``package_reports``)
   * - ``patchmon.core.host`` present
     - Auto-Enrollment token
   * - ``patchmon.core.host`` desired-state fields
     - Integration ``host:get`` plus ``host:patch`` and/or ``host:put``
   * - ``patchmon.core.host`` absent
     - Integration ``host:delete``
   * - ``patchmon.core.host_action``
     - Integration ``host:update``
   * - ``patchmon.core.host_token`` script
     - Auto-Enrollment token
   * - ``patchmon.core.host_token`` present/absent
     - Admin JWT (Manage Settings)
   * - ``patchmon.core.agent``
     - Auto-Enrollment token (install)
   * - ``patchmon.core.host`` role
     - See the tables above by ``host_state`` and by which managed fields are set

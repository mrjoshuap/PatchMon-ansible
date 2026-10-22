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
     - Inventory, ``host_info``, ``host_packages``, lookup, host delete
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

Friendly name, notes, auto-update, host-down alerts, group membership, fetch-report, force-agent-update, and regenerate-credentials are also session routes under ``/api/v1/hosts/...``. This collection does not call them. See :ref:`ansible_collections.patchmon.core.docsite.patchmon_feedback`.

Integration API scopes
----------------------

Scopes are explicit. ``get`` does not imply ``delete``.

.. list-table::
   :header-rows: 1
   :widths: 16 84

   * - Scope
     - Capabilities in this collection
   * - ``host:get``
     - Inventory plugin, ``host_info`` (including ``notes``, ``package_reports``, ``agent_queue``), ``host_packages``, ``lookup('patchmon.core.host')``, ``report_health`` role, ``apply_security_updates`` apt opt-in (``host_packages``), existence checks before enroll
   * - ``host:delete``
     - ``patchmon.core.host`` with ``state=absent``, ``roles/host`` when ``host_state=absent``

There is no Integration ``host:create`` scope. Host creation uses the Auto-Enrollment API. There is no Integration route for host field changes, group replacement, or host commands. Those stay on the signed-in UI API.

The only Integration write this collection calls is ``DELETE /api/v1/api/hosts/{id}`` (``host:delete``).

``GET /api/v1/api/hosts`` returns ``host_groups`` on each host. The inventory ``hostgroup`` query accepts a group id or the exact PatchMon name. ``GET /api/v1/api/host-groups`` is not on the Integration API, so an Ansible ``patchmon_<slug>`` token is not translated.

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
4. **Token minting** (create enrollment tokens from Ansible): admin JWT only on trusted Controllers; prefer creating tokens in the UI and injecting key/secret via Vault / AAP credentials.
5. Store secrets in Ansible Vault, AAP Credential, or environment variables — never commit plaintext keys.
6. Keep ``verify_ssl: true`` outside lab environments.

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
     - Missing scope (``host:get`` / ``host:delete``) or enrollment IP not allowed
   * - 404
     - Unknown host
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
   * - ``patchmon.core.apply_security_updates``
     - None for dnf and dnf5. Integration ``host:get`` when ``apply_security_updates_try_listed`` is true and the package manager is apt (``host_packages``). Agent report is local.
   * - ``patchmon.core.apply_all_updates``
     - None. Local package upgrades and a local agent report.
   * - ``patchmon.core.reboot_needed``
     - None. Local reboot and a local agent report.
   * - ``patchmon.core.host`` present
     - Auto-Enrollment token
   * - ``patchmon.core.host`` absent
     - Integration ``host:delete``
   * - ``patchmon.core.host_token`` script
     - Auto-Enrollment token
   * - ``patchmon.core.host_token`` present/absent
     - Admin JWT (Manage Settings)
   * - ``patchmon.core.agent``
     - Auto-Enrollment token (install)
   * - ``patchmon.core.host`` role
     - Auto-Enrollment when ``host_state=present``; Integration ``host:delete`` when ``host_state=absent``

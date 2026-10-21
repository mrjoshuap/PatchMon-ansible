.. _ansible_collections.patchmon.core.docsite.troubleshooting:

Troubleshooting
===============

Check the API from the control node before debugging Ansible. Use the same Integration token the inventory plugin uses.

.. code-block:: bash

   curl -u "$PATCHMON_API_KEY:$PATCHMON_API_SECRET" \
     -H 'Accept: application/json' \
     "$PATCHMON_API_URL"
   curl -u "$PATCHMON_API_KEY:$PATCHMON_API_SECRET" \
     -H 'Accept: application/json' \
     "${PATCHMON_API_URL}?include=stats"

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Symptom
     - What to check
   * - Plugin not found or ignored
     - The collection is installed, ``enable_plugins`` includes ``patchmon.core.inventory``, and the inventory filename ends in ``.yml`` or ``.yaml``.
   * - HTTP 401 or 403
     - ``PATCHMON_API_KEY`` and ``PATCHMON_API_SECRET`` are the Integration token, and the token has the scope that call needs. ``host:get`` does not imply ``host:patch``, ``host:put``, ``host:update``, or ``host:delete``. Creating a host or installing the agent needs Auto-Enrollment, not this token. See :ref:`ansible_collections.patchmon.core.docsite.permissions`.
   * - Empty inventory
     - Hosts are enrolled in PatchMon, and ``hostgroup`` is not filtering them out. An exact name such as ``No Reboot`` is not the same group as ``No_Reboot``.
   * - Redirect or empty body
     - Use ``https://<patchmon>/api/v1/api/hosts`` without a trailing slash that returns a redirect.
   * - TLS errors
     - Outside a lab, leave ``verify_ssl: true``. In a lab, set ``verify_ssl: false`` or ``PATCHMON_VERIFY_SSL=false``.
   * - No ``patchmon_needs_reboot`` group
     - The inventory has ``include_stats: true`` and ``auto_groups: true``. ``stats_var_scope: targeting`` still builds those groups. It only omits telemetry hostvars.
   * - Agent install returns 401 ``Invalid or inactive token``
     - The enrollment script must be written with ``host_token`` ``dest`` and copied to the host. Returning the script body lets Ansible ``no_log`` replace the key inside the script with ``********``.
   * - ``host_state=absent`` does nothing or fails validation
     - Set ``host_id`` (inventory ``patchmon_id`` after a stats inventory refresh). An empty id skips a delete so a host that never enrolled can still be removed from Ansible.

Credential types and HTTP status codes are in :ref:`ansible_collections.patchmon.core.docsite.permissions`. Upgrades from ``patchmon.dynamic_inventory`` 1.0.0 are in :ref:`ansible_collections.patchmon.core.docsite.migrating_to_2.0`.

.. _ansible_collections.patchmon.core.docsite.migrating_to_2.0:

Migrating to patchmon.core 2.0.0
================================

This is a breaking upgrade from ``patchmon.dynamic_inventory`` 1.0.0.
There are no compatibility redirects — update installs and inventory YAML as below.

1. Install the new collection
-----------------------------

.. code-block:: bash

   ansible-galaxy collection install patchmon.core
   # or from a release tarball:
   # ansible-galaxy collection install ./patchmon-core-2.0.0.tar.gz

You can remove the old collection if it is still installed:

.. code-block:: bash

   ansible-galaxy collection remove patchmon.dynamic_inventory

2. Update inventory configuration
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - 1.0.0
     - 2.0.0
   * - Collection ``patchmon.dynamic_inventory``
     - Collection ``patchmon.core``
   * - ``plugin: patchmon.dynamic_inventory.dynamic_inventory``
     - ``plugin: patchmon.core.inventory``

``ansible.cfg``:

.. code-block:: ini

   [inventory]
   enable_plugins = patchmon.core.inventory

Inventory file:

.. code-block:: yaml

   ---
   plugin: patchmon.core.inventory
   api_url: https://patchmon.example.com/api/v1/api/hosts
   api_key: "{{ lookup('env', 'PATCHMON_API_KEY') }}"
   api_secret: "{{ lookup('env', 'PATCHMON_API_SECRET') }}"
   verify_ssl: true

3. FQCN map (1.0.0 → 2.0.0)
---------------------------

1.0.0 shipped only the inventory plugin. Anything added later under interim names should use the 2.0.0 FQCNs:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Kind
     - Use in 2.0.0
   * - Inventory
     - ``patchmon.core.inventory``
   * - Module
     - ``patchmon.core.host_info``
   * - Module
     - ``patchmon.core.host_packages``
   * - Module
     - ``patchmon.core.host``
   * - Module
     - ``patchmon.core.host_token``
   * - Lookup
     - ``lookup('patchmon.core.host', …)``
   * - Role
     - ``patchmon.core.agent``
   * - Role
     - ``patchmon.core.host``

4. Credentials (new in 2.0.0 write paths)
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Use case
     - Credential
   * - Inventory / info / packages / lookup
     - Integration API (``host:get``)
   * - Enroll hosts / install agent
     - Auto-Enrollment key + secret
   * - Delete hosts
     - Integration API (``host:delete``)

See :ref:`ansible_collections.patchmon.core.docsite.permissions`.

5. Stats hostvars and facts
---------------------------

``include_stats: true`` still sets ``patchmon_*`` host variables. ``stats_var_scope`` defaults to ``all`` (every stats hostvar). Set ``targeting`` to keep only the fields that build groups or gate plays:

- kept: ``patchmon_needs_reboot``, ``patchmon_update_state``, ``patchmon_security_updates_count``, ``patchmon_os_type``, ``patchmon_effective_status``, ``patchmon_reporting_state``
- omitted: ``patchmon_updates_count``, ``patchmon_total_packages``, ``patchmon_last_update``, ``patchmon_os_version``, ``patchmon_status``

Auto groups are unchanged. ``compose`` / ``keyed_groups`` / ``groups`` that read an omitted name need ``stats_var_scope: all``.

Telemetry belongs in ``ansible_facts.patchmon`` from ``patchmon.core.host_info`` (``inject_facts: true``, default ``false``). Those keys have no ``patchmon_`` prefix, so they do not override inventory hostvars. The inventory plugin does not write facts.

6. Smoke-test after migration
-----------------------------

.. code-block:: bash

   export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
   export PATCHMON_API_KEY='...'
   export PATCHMON_API_SECRET='...'

   ansible-inventory -i inventories/patchmon.yml --graph
   ansible-doc patchmon.core.inventory
   ansible-doc patchmon.core.host_info

Copy-paste examples: `examples guide <https://github.com/mrjoshuap/PatchMon-ansible/blob/main/examples/README.md>`_.

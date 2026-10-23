.. _ansible_collections.patchmon.core.docsite.quick_start:

Quick start
===========

Install ``patchmon.core``, point an inventory file at your PatchMon server, and run one read-only playbook. The :ref:`ansible_collections.patchmon.core.docsite.readme` page is the full reference, including the fleet diagrams.

1. Install the collection
-------------------------

.. code-block:: bash

   ansible-galaxy collection install patchmon.core
   pip install 'requests>=2.25.1'

Air-gapped installs use the release tarball described in the README.

2. Enable the inventory plugin
------------------------------

.. code-block:: ini

   [inventory]
   enable_plugins = patchmon.core.inventory

3. Create an inventory file
---------------------------

.. code-block:: bash

   mkdir -p inventories
   cp examples/patchmon_inventory_stats.yml inventories/patchmon.yml

Export ``PATCHMON_SERVER_URL`` and leave ``api_url`` unset. The plugin derives ``https://<your-patchmon>/api/v1/api/hosts``. Setting ``api_url`` or ``PATCHMON_API_URL`` overrides that URL and is discouraged. An instance root passed as ``api_url`` still works. The plugin appends ``/api/v1/api/hosts``.

4. Export Integration API credentials
-------------------------------------

Create a token under **Settings → Integrations → API** with at least ``host:get``.

.. code-block:: bash

   export PATCHMON_SERVER_URL='https://patchmon.example.com'
   export PATCHMON_API_KEY='<token key>'
   export PATCHMON_API_SECRET='<token secret>'
   # Optional TLS. true is the default. false is for a lab only.
   # export PATCHMON_VERIFY_SSL=true
   # PATCHMON_API_URL overrides the derived hosts URL and is discouraged.
   # Enrollment uses the same server URL. PATCHMON_ENROLLMENT_URL overrides
   # the derived /api/v1/auto-enrollment URL and is discouraged.

Do not commit the key or secret. Installing an agent or creating a host needs a separate Auto-Enrollment token. See :ref:`ansible_collections.patchmon.core.docsite.permissions`.

5. List hosts
-------------

.. code-block:: bash

   ansible-inventory -i inventories/patchmon.yml --graph

With ``include_stats: true`` and ``auto_groups: true``, expect groups such as ``patchmon_security_required`` and ``patchmon_needs_reboot``. A PatchMon group named ``No Reboot`` becomes ``patchmon_no_reboot`` when that slug is unique.

6. Run a read-only playbook
---------------------------

.. code-block:: bash

   ansible-playbook -i inventories/patchmon.yml examples/playbooks/pending_updates.yml \
     --limit patchmon_security_required

Modules call the API from the control node (``delegate_to: localhost``). Copy-paste examples live in ``examples/playbooks/`` in the `collection repository <https://github.com/mrjoshuap/PatchMon-ansible/tree/main/examples>`_.

7. Enroll, maintain, and retire
-------------------------------

The same directory has the fleet plays from the README diagram. ``maintain.yml`` refreshes inventory, checks report health (``patchmon.core.report_health``), applies security-only updates (``patchmon.core.apply_security_updates``), and reboots Automated hosts one at a time (``patchmon.core.reboot_needed``). All pending upgrades are ``apply_all_updates.yml`` (``patchmon.core.apply_all_updates``). ``retire.yml`` removes the agent and deletes the host record. It requires ``--limit``.

``enroll.yml`` needs an Auto-Enrollment token (``PATCHMON_ENROLLMENT_KEY`` and ``PATCHMON_ENROLLMENT_SECRET``) and ``PATCHMON_SERVER_URL``. The new host stays in that token's default group. Setting ``PATCHMON_ENROLLMENT_URL`` directly is discouraged.

.. code-block:: bash

   ansible-playbook -i inventories/linux.yml examples/playbooks/enroll.yml --limit web01.example.com
   ansible-playbook -i inventories/patchmon.yml examples/playbooks/maintain.yml
   ansible-playbook -i inventories/patchmon.yml examples/playbooks/apply_all_updates.yml
   ansible-playbook -i inventories/patchmon.yml examples/playbooks/retire.yml --limit web01.example.com

If the graph is empty or the plugin is ignored, use :ref:`ansible_collections.patchmon.core.docsite.troubleshooting`.

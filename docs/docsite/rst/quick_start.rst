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

Edit ``api_url`` so it is ``https://<your-patchmon>/api/v1/api/hosts``. The instance root also works. The plugin appends ``/api/v1/api/hosts``.

4. Export Integration API credentials
-------------------------------------

Create a token under **Settings → Integrations → API** with at least ``host:get``.

.. code-block:: bash

   export PATCHMON_API_URL='https://patchmon.example.com/api/v1/api/hosts'
   export PATCHMON_API_KEY='<token key>'
   export PATCHMON_API_SECRET='<token secret>'

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

If the graph is empty or the plugin is ignored, use :ref:`ansible_collections.patchmon.core.docsite.troubleshooting`.

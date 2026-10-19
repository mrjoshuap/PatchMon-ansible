# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the host_token module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.ansible.plugins.modules import host_token as mod


def test_script_fetch(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "script",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": "ek",
                "enrollment_secret": "es",
                "script_type": "direct-host",
                "force": False,
                "admin_token": None,
                "token_name": None,
                "token_id": None,
                "max_hosts_per_day": 100,
                "default_host_group_id": None,
                "allowed_ip_ranges": None,
                "expires_at": None,
                "metadata": None,
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeEnrollment(object):
        def __init__(self, *args, **kwargs):
            pass

        def get_script(self, script_type="direct-host", force=False):
            return "#!/bin/bash\necho ok\n"

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonEnrollmentClient", FakeEnrollment)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is False
    assert "bash" in exits["script"]


def test_create_token(monkeypatch):
    exits = {}

    class FakeModule(object):
        def __init__(self, *args, **kwargs):
            self.check_mode = False
            self.params = {
                "state": "present",
                "server_url": "https://patchmon.example.com",
                "enrollment_key": None,
                "enrollment_secret": None,
                "script_type": "direct-host",
                "force": False,
                "admin_token": "jwt",
                "token_name": "ansible",
                "token_id": None,
                "max_hosts_per_day": 50,
                "default_host_group_id": None,
                "allowed_ip_ranges": None,
                "expires_at": None,
                "metadata": None,
                "verify_ssl": True,
                "timeout": 30,
            }

        def fail_json(self, **kwargs):
            raise SystemExit(kwargs)

        def exit_json(self, **kwargs):
            exits.update(kwargs)
            raise SystemExit(0)

    class FakeAdmin(object):
        def __init__(self, *args, **kwargs):
            pass

        def create_enrollment_token(self, **kwargs):
            return {
                "message": "created",
                "token": {
                    "token_name": kwargs["token_name"],
                    "token_key": "k",
                    "token_secret": "s",
                },
                "warning": "Save the token_secret now",
            }

    monkeypatch.setattr(mod, "AnsibleModule", FakeModule)
    monkeypatch.setattr(mod, "PatchMonAdminClient", FakeAdmin)
    monkeypatch.setattr(mod, "HAS_REQUESTS", True)

    with pytest.raises(SystemExit):
        mod.run_module()

    assert exits["changed"] is True
    assert exits["token"]["token_key"] == "k"

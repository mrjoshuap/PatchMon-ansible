# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for PatchMon group name mapping."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.patchmon.core.plugins.module_utils.group_names import (
    GroupNameError,
    assign_ansible_group_names,
    resolve_group_id,
)

SPACE_AND_UNDERSCORE = [
    {"id": "g-space", "name": "No Reboot"},
    {"id": "g-under", "name": "No_Reboot"},
]


def test_unique_space_uses_patchmon_slug():
    assigned = assign_ansible_group_names([{"id": "g1", "name": "No Reboot"}])
    assert assigned["g1"] == "patchmon_no_reboot"


def test_collision_appends_sanitized_group_id():
    assigned = assign_ansible_group_names(SPACE_AND_UNDERSCORE)
    assert assigned["g-space"] == "patchmon_no_reboot_g_space"
    assert assigned["g-under"] == "patchmon_no_reboot_g_under"


def test_exact_name_distinguishes_space_from_underscore():
    assert resolve_group_id("No Reboot", SPACE_AND_UNDERSCORE) == "g-space"
    assert resolve_group_id("No_Reboot", SPACE_AND_UNDERSCORE) == "g-under"


def test_sanitized_token_is_ambiguous_when_both_forms_exist():
    with pytest.raises(GroupNameError, match="exact name"):
        resolve_group_id("patchmon_no_reboot", SPACE_AND_UNDERSCORE)


def test_sanitized_token_matches_the_only_group():
    catalog = [{"id": "g1", "name": "No Reboot"}]
    assert resolve_group_id("No_Reboot", catalog) == "g1"
    assert resolve_group_id("patchmon_no_reboot", catalog) == "g1"
    assert resolve_group_id("g1", catalog) == "g1"


def test_id_suffixed_ansible_group_resolves_when_names_collide():
    assigned = assign_ansible_group_names(SPACE_AND_UNDERSCORE)
    assert resolve_group_id(assigned["g-space"], SPACE_AND_UNDERSCORE) == "g-space"


def test_reserved_stats_group_name_does_not_select_a_host_group():
    catalog = [{"id": "g1", "name": "needs reboot"}]
    assigned = assign_ansible_group_names(catalog)
    assert assigned["g1"].startswith("patchmon_needs_reboot_")
    with pytest.raises(GroupNameError, match="not a unique"):
        resolve_group_id("patchmon_needs_reboot", catalog)
    assert resolve_group_id("needs reboot", catalog) == "g1"

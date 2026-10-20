# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Map PatchMon host-group names onto Ansible groups and back.

Ansible group names cannot contain spaces. Inventory sanitizing replaces each
invalid character (space, hyphen, and the like) with ``_``, so ``No Reboot``
and ``No_Reboot`` become the same token. Exact PatchMon names and group ids
stay distinct. A shared sanitized token is accepted only when one group
produces it.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

from ansible.module_utils.common.text.converters import to_text

# ansible.constants.INVALID_VARIABLE_NAMES, applied the way inventory
# ``_sanitize_group_name`` does (``to_safe_group_name(..., force=True)``).
_INVALID_GROUP_CHARS = re.compile(r"^[\d\W]|[^\w]")

GROUP_PREFIX = "patchmon_"

# Stats auto-groups from the inventory plugin. Host groups must not reuse them.
RESERVED_ANSIBLE_GROUPS = frozenset(
    (
        "patchmon_needs_reboot",
        "patchmon_security_required",
        "patchmon_updates_pending",
        "patchmon_up_to_date",
        "patchmon_stale",
        "patchmon_overdue",
        "patchmon_inactive",
    )
)


class GroupNameError(Exception):
    """Raised when a group token does not map to exactly one PatchMon group."""


def sanitize_group_name(name):
    """Replace characters Ansible rejects in group names with ``_``."""
    return _INVALID_GROUP_CHARS.sub("_", to_text(name))


def group_slug(name):
    """Lowercase sanitized name, used under the ``patchmon_`` prefix."""
    return sanitize_group_name(name).lower()


def preferred_ansible_group(name):
    """``patchmon_<slug>`` before collision or reserved-name suffixes."""
    slug = group_slug(name).strip("_")
    if not slug:
        slug = "unnamed"
    return GROUP_PREFIX + slug


def is_reserved_ansible_group(name):
    """True for built-in stats groups, including ``patchmon_os_<type>``."""
    text = to_text(name)
    if text in RESERVED_ANSIBLE_GROUPS:
        return True
    return text.startswith("patchmon_os_") and text != "patchmon_os_"


def group_key(group):
    """Stable catalog key. Prefers the PatchMon group id."""
    if not isinstance(group, dict):
        raise GroupNameError("host group entries must be mappings")
    group_id = group.get("id")
    if group_id:
        return to_text(group_id)
    return "name:{0}".format(to_text(group.get("name") or ""))


def assign_ansible_group_names(groups):
    """Return ``{catalog key: ansible group name}``.

    A unique sanitized name becomes ``patchmon_<slug>``. When two PatchMon
    groups share that slug, or the slug is a stats auto-group, the group id
    is appended: ``patchmon_<slug>_<id>``.
    """
    seen = {}
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        name = group.get("name")
        if name is None or to_text(name).strip() == "":
            continue
        key = group_key(group)
        seen[key] = {
            "key": key,
            "id": to_text(group["id"]) if group.get("id") else None,
            "name": to_text(name),
        }
    items = list(seen.values())

    buckets = {}
    for row in items:
        preferred = preferred_ansible_group(row["name"])
        row["preferred"] = preferred
        buckets.setdefault(preferred, []).append(row["key"])

    assigned = {}
    for row in items:
        preferred = row["preferred"]
        if len(buckets[preferred]) == 1 and not is_reserved_ansible_group(
            preferred
        ):
            assigned[row["key"]] = preferred
            continue
        if not row["id"]:
            raise GroupNameError(
                "PatchMon group {0!r} needs its id to build a unique Ansible "
                "group name. It collides with {1}.".format(
                    row["name"], preferred
                )
            )
        assigned[row["key"]] = "{0}_{1}".format(
            preferred, sanitize_group_name(row["id"]).lower()
        )

    used = {}
    for key, ansible_name in assigned.items():
        used.setdefault(ansible_name, []).append(key)
    for ansible_name, keys in list(used.items()):
        if len(keys) == 1 and not is_reserved_ansible_group(ansible_name):
            continue
        for key in keys:
            row = seen[key]
            if not row["id"]:
                raise GroupNameError(
                    "PatchMon group {0!r} needs its id to build a unique "
                    "Ansible group name.".format(row["name"])
                )
            assigned[key] = "patchmon_id_{0}".format(
                sanitize_group_name(row["id"]).lower()
            )
    return assigned


def _candidate_slugs(token):
    slugs = {group_slug(token)}
    lowered = to_text(token).lower()
    if lowered.startswith(GROUP_PREFIX):
        slugs.add(group_slug(lowered[len(GROUP_PREFIX) :]))
    return slugs


def _format_candidates(rows):
    return ", ".join(
        "{0!r} (id {1})".format(row["name"], row["id"]) for row in rows
    )


def resolve_group_id(token, groups):
    """Map a name, Ansible group, or id to one PatchMon group id.

    Exact names win over sanitized names, so a space and an underscore stay
    different groups. A sanitized token is accepted only when one group
    produces it.
    """
    text = to_text(token).strip() if token is not None else ""
    if not text:
        raise GroupNameError(
            "groups entries must be non-empty names or UUIDs"
        )

    catalog = []
    for group in groups or []:
        if not isinstance(group, dict) or not group.get("id"):
            continue
        name = group.get("name")
        catalog.append(
            {
                "id": to_text(group["id"]),
                "name": to_text(name) if name is not None else "",
            }
        )

    for row in catalog:
        if text == row["id"]:
            return row["id"]

    named = [row for row in catalog if row["name"]]
    exact = [row for row in named if row["name"] == text]
    if len(exact) == 1:
        return exact[0]["id"]
    if len(exact) > 1:
        raise GroupNameError(
            "host group {0!r} matches more than one PatchMon group. "
            "Pass the group id. Candidates: {1}".format(
                text, _format_candidates(exact)
            )
        )

    assigned = assign_ansible_group_names(named)
    by_ansible = {}
    for row in named:
        by_ansible.setdefault(assigned[row["id"]], []).append(row)
    ansible_hits = by_ansible.get(text) or []
    if len(ansible_hits) == 1:
        return ansible_hits[0]["id"]
    if len(ansible_hits) > 1:
        raise GroupNameError(
            "host group {0!r} matches more than one PatchMon group. "
            "Pass the group id. Candidates: {1}".format(
                text, _format_candidates(ansible_hits)
            )
        )

    slugs = _candidate_slugs(text)
    slug_hits = [row for row in named if group_slug(row["name"]) in slugs]
    friendly = [
        row
        for row in slug_hits
        if assigned[row["id"]] == preferred_ansible_group(row["name"])
    ]
    if len(friendly) == 1:
        return friendly[0]["id"]
    if len(slug_hits) > 1:
        raise GroupNameError(
            "host group {0!r} matches more than one PatchMon group after "
            "replacing spaces and other invalid characters with '_'. "
            "Pass the group id or the exact name. Candidates: {1}".format(
                text, _format_candidates(slug_hits)
            )
        )
    if len(slug_hits) == 1:
        row = slug_hits[0]
        preferred = preferred_ansible_group(row["name"])
        if text == preferred or is_reserved_ansible_group(text):
            raise GroupNameError(
                "host group {0!r} is not a unique PatchMon group name. "
                "The matching group is {1!r} (id {2}, Ansible group {3}). "
                "Pass that id or the exact name.".format(
                    text, row["name"], row["id"], assigned[row["id"]]
                )
            )
        return row["id"]

    raise GroupNameError(
        "host group {0!r} did not match exactly one group".format(text)
    )


def resolve_group_ids(tokens, groups):
    """Resolve a list of names or ids, preserving order and dropping dupes."""
    if not isinstance(tokens, list):
        raise GroupNameError("groups must be a list")
    resolved = []
    seen = set()
    for raw in tokens:
        group_id = resolve_group_id(raw, groups)
        if group_id not in seen:
            seen.add(group_id)
            resolved.append(group_id)
    return resolved

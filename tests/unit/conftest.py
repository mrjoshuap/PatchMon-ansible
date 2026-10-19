# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Make the collection importable as ansible_collections.patchmon.ansible."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys


def pytest_configure(config):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    collections_root = os.path.join(repo_root, ".pytest_collections")
    namespace_dir = os.path.join(
        collections_root, "ansible_collections", "patchmon"
    )
    collection_link = os.path.join(namespace_dir, "ansible")

    os.makedirs(namespace_dir, exist_ok=True)
    if os.path.lexists(collection_link):
        if os.path.islink(collection_link) or os.path.isdir(collection_link):
            if os.path.realpath(collection_link) != repo_root:
                if os.path.islink(collection_link):
                    os.unlink(collection_link)
                # leave existing non-link dirs alone
        if not os.path.lexists(collection_link):
            os.symlink(repo_root, collection_link)
    else:
        os.symlink(repo_root, collection_link)

    if collections_root not in sys.path:
        sys.path.insert(0, collections_root)

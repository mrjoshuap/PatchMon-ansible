# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Make the collection importable as ansible_collections.patchmon.core."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import shutil
import sys


def pytest_configure(config):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    collections_root = os.path.join(repo_root, ".collections")
    namespace_dir = os.path.join(collections_root, "ansible_collections", "patchmon")
    collection_link = os.path.join(namespace_dir, "core")

    os.makedirs(namespace_dir, exist_ok=True)
    # A real directory here is a Galaxy install and would shadow the checkout.
    if os.path.lexists(collection_link) and not os.path.islink(collection_link):
        shutil.rmtree(collection_link)
    if os.path.islink(collection_link):
        if os.path.realpath(collection_link) != repo_root:
            os.remove(collection_link)
    if not os.path.lexists(collection_link):
        os.symlink(repo_root, collection_link)

    if collections_root not in sys.path:
        sys.path.insert(0, collections_root)

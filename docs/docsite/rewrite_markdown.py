#!/usr/bin/env python
"""Rewrite README and CHANGELOG links for the Sphinx docsite."""

from __future__ import annotations

import os
import re
import sys

GITHUB_BLOB = "https://github.com/mrjoshuap/PatchMon-ansible/blob/main/"
GITHUB_TREE = "https://github.com/mrjoshuap/PatchMon-ansible/tree/main/"
DOC_LINKS = {
    "docs/permissions.md": "permissions.md",
    "docs/migrating_to_2.0.md": "migrating_to_2.0.md",
    "CHANGELOG.md": "changelog.md",
}
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def rewrite_link(match: re.Match[str]) -> str:
    url = match.group(1)
    if url.startswith(("http://", "https://", "#", "mailto:")):
        return match.group(0)
    path, _sep, _anchor = url.partition("#")
    if path in DOC_LINKS:
        return "](" + DOC_LINKS[path] + ")"
    if path == "examples/README.md":
        return "](quick_start.md)"
    if url.endswith("/"):
        return "](" + GITHUB_TREE + url + ")"
    return "](" + GITHUB_BLOB + url + ")"


def rewrite(text: str) -> str:
    text = text.replace("<patchmon-host>", "patchmon.example.com")
    return LINK_RE.sub(rewrite_link, text)


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dest = os.path.join(root, "built-docs", "included")
    os.makedirs(dest, exist_ok=True)
    for name in ("README.md", "CHANGELOG.md"):
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            rewritten = rewrite(handle.read())
        with open(os.path.join(dest, name), "w", encoding="utf-8") as handle:
            handle.write(rewritten)
    return 0


if __name__ == "__main__":
    sys.exit(main())

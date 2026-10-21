#!/usr/bin/env python
"""Rewrite README, CHANGELOG, and PROPOSAL links for the Sphinx docsite."""

from __future__ import annotations

import os
import re
import sys

GITHUB_BLOB = "https://github.com/mrjoshuap/PatchMon-ansible/blob/main/"
GITHUB_TREE = "https://github.com/mrjoshuap/PatchMon-ansible/tree/main/"
# MyST turns a link that ends in .md into a heading on the current page
# (readme.html#permissions.md). Docsite pages are sibling HTML files.
DOC_LINKS = {
    "docs/permissions.md": "permissions.html",
    "docs/migrating_to_2.0.md": "migrating_to_2.0.html",
    "CHANGELOG.md": "changelog.html",
    "PROPOSAL.md": "proposal.html",
    "examples/README.md": "quick_start.html",
}
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def rewrite_link(match: re.Match[str]) -> str:
    url = match.group(1)
    if url.startswith(("http://", "https://", "#", "mailto:")):
        return match.group(0)
    path, sep, anchor = url.partition("#")
    if path in DOC_LINKS:
        target = DOC_LINKS[path]
        if sep:
            target += "#" + anchor
        return "](" + target + ")"
    if url.endswith("/"):
        return "](" + GITHUB_TREE + url + ")"
    return "](" + GITHUB_BLOB + url + ")"


def strip_title(text: str) -> str:
    """The RST page supplies the title. Drop the Markdown H1 so it is not repeated."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        if lines and lines[0].strip() == "":
            lines = lines[1:]
    return "".join(lines)


def rewrite(text: str) -> str:
    text = text.replace("<patchmon-host>", "patchmon.example.com")
    return strip_title(LINK_RE.sub(rewrite_link, text))


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dest = os.path.join(root, "built-docs", "included")
    os.makedirs(dest, exist_ok=True)
    for name in ("README.md", "CHANGELOG.md", "PROPOSAL.md"):
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            rewritten = rewrite(handle.read())
        with open(os.path.join(dest, name), "w", encoding="utf-8") as handle:
            handle.write(rewritten)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""Rewrite guide and project Markdown links for the Sphinx docsite."""

from __future__ import annotations

import os
import posixpath
import re
import sys

GITHUB_BLOB = "https://github.com/mrjoshuap/PatchMon-ansible/blob/main/"
GITHUB_TREE = "https://github.com/mrjoshuap/PatchMon-ansible/tree/main/"
# Paths are relative to the repository root. Docsite pages are siblings under
# docsite/, so the rewrite target is the HTML filename Sphinx emits.
DOC_LINKS = {
    "docs/automator-guide.md": "automator_guide.html",
    "docs/developer-guide.md": "developer_guide.html",
    "CHANGELOG.md": "changelog.html",
    "PROPOSAL.md": "proposal.html",
    "PATCHMON-FEEDBACK.md": "patchmon_feedback.html",
    "docs/permissions.md": "automator_guide.html#chapter-3-credentials",
    "docs/migrating_to_2.0.md": "automator_guide.html#chapter-9-migrating-from-1-0",
}
# (repo-relative markdown path, directory used to resolve relative links)
SOURCES = (
    ("CHANGELOG.md", ""),
    ("PROPOSAL.md", ""),
    ("PATCHMON-FEEDBACK.md", ""),
    ("docs/automator-guide.md", "docs"),
    ("docs/developer-guide.md", "docs"),
)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n+", re.DOTALL)


def mapped_target(norm: str, anchor: str) -> str | None:
    target = DOC_LINKS.get(norm)
    if target is None:
        return None
    page, _, mapped_anchor = target.partition("#")
    if anchor:
        return page + "#" + anchor
    if mapped_anchor:
        return page + "#" + mapped_anchor
    return page


def rewrite_link(match: re.Match[str], base: str) -> str:
    url = match.group(1)
    if url.startswith(("http://", "https://", "#", "mailto:")):
        return match.group(0)
    path, sep, anchor = url.partition("#")
    if path.endswith(".html"):
        return match.group(0)
    norm = posixpath.normpath(posixpath.join(base, path)) if path else ""
    target = mapped_target(norm, anchor)
    if target is not None:
        return "](" + target + ")"
    if not path:
        return match.group(0)
    if url.endswith("/"):
        return "](" + GITHUB_TREE + norm + "/)"
    suffix = ("#" + anchor) if sep else ""
    return "](" + GITHUB_BLOB + norm + suffix + ")"


def strip_title(text: str) -> str:
    """The RST page supplies the title. Drop the Markdown H1 so it is not repeated."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        if lines and lines[0].strip() == "":
            lines = lines[1:]
    return "".join(lines)


def rewrite(text: str, base: str) -> str:
    text = FRONTMATTER_RE.sub("", text)
    text = text.replace("<patchmon-host>", "patchmon.example.com")
    return strip_title(LINK_RE.sub(lambda match: rewrite_link(match, base), text))


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dest = os.path.join(root, "built-docs", "included")
    os.makedirs(dest, exist_ok=True)
    for name, base in SOURCES:
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            rewritten = rewrite(handle.read(), base)
        with open(
            os.path.join(dest, os.path.basename(name)), "w", encoding="utf-8"
        ) as handle:
            handle.write(rewritten)
    return 0


if __name__ == "__main__":
    sys.exit(main())

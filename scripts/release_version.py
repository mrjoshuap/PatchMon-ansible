#!/usr/bin/env python3
"""Choose the Galaxy version for a stable tag or a main-branch development build.

galaxy.yml ``version:`` is the next release, written as ``X.Y.Z``. A tag
``vX.Y.Z`` publishes that exact version. A push to ``main`` publishes
``X.Y.Z-dev.<UTC timestamp>``, which sorts before ``X.Y.Z``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
TAG_RE = re.compile(r"^refs/tags/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
DEV_TAG_RE = re.compile(
    r"^refs/tags/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-dev\.[0-9]{14}$"
)
FIELD_RE = r"(?m)^{key}:\s*['\"]?([^'\"\s#]+)['\"]?\s*$"
FLOOR = "2.0.0"
FQCN = "patchmon.core"
GALAXY_VERSIONS = (
    "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/"
    "collections/index/{namespace}/{name}/versions/?limit=100"
)


class ReleaseError(Exception):
    """The ref or galaxy.yml cannot produce a version."""


def field(text: str, key: str) -> str:
    match = re.search(FIELD_RE.format(key=re.escape(key)), text)
    if match is None:
        raise ReleaseError(f"galaxy.yml is missing {key}")
    return match.group(1)


def load_galaxy(path: Path) -> tuple[str, str, str, str]:
    text = path.read_text()
    namespace = field(text, "namespace")
    name = field(text, "name")
    version = field(text, "version")
    if VERSION_RE.fullmatch(version) is None:
        raise ReleaseError(
            f"galaxy.yml version must be X.Y.Z with no v prefix and no prerelease "
            f"(found {version})"
        )
    if len(re.findall(r"(?m)^version:\s*", text)) != 1:
        raise ReleaseError("galaxy.yml must contain one version: line")
    return text, namespace, name, version


def replace_version(text: str, version: str) -> str:
    updated, count = re.subn(
        r"(?m)^version:\s*\S+\s*$",
        f"version: {version}",
        text,
        count=1,
    )
    if count != 1:
        raise ReleaseError("could not rewrite galaxy.yml version")
    return updated


def core(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split("-", 1)[0].split(".")
    return int(major), int(minor), int(patch)


def newer_than_floor(version: str, floor: str = FLOOR) -> bool:
    """True when a prerelease would still match ``>=floor``."""
    return core(version) > core(floor)


def galaxy_has_stable(namespace: str, name: str) -> bool:
    url = GALAXY_VERSIONS.format(namespace=namespace, name=name)
    while url:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            raise ReleaseError(
                f"Galaxy version lookup failed: HTTP {exc.code}"
            ) from exc
        for item in payload.get("data", []):
            if VERSION_RE.fullmatch(str(item.get("version", ""))):
                return True
        next_link = (payload.get("links") or {}).get("next")
        url = (
            urllib.parse.urljoin("https://galaxy.ansible.com", next_link)
            if next_link
            else ""
        )
    return False


def decide(ref: str, base: str, timestamp: str) -> tuple[str, str, str]:
    if DEV_TAG_RE.fullmatch(ref):
        return "skip", "", ""
    tag_match = TAG_RE.fullmatch(ref)
    if tag_match:
        version = ".".join(tag_match.groups())
        if version != base:
            raise ReleaseError(
                f"tag v{version} does not match galaxy.yml version {base}. "
                "Tag the commit whose version: is that release, then bump version: "
                "on main to the next release."
            )
        return "stable", version, f"v{version}"
    if ref != "refs/heads/main":
        raise ReleaseError(f"unsupported ref {ref}")
    if re.fullmatch(r"[0-9]{14}", timestamp) is None:
        raise ReleaseError("timestamp must be 14 UTC digits YYYYMMDDHHMMSS")
    version = f"{base}-dev.{timestamp}"
    return "dev", version, f"v{version}"


def release_notes(channel: str, version: str, base: str) -> str:
    if channel == "stable":
        return (
            f"{FQCN} {version}\n\n"
            "Stable release.\n\n"
            "```bash\n"
            f"ansible-galaxy collection install '{FQCN}:>={version}'\n"
            "```\n\n"
            "`version:` in `galaxy.yml` on `main` is the next release. "
            "Bump it after this tag, before the next push to `main`.\n"
        )
    return (
        f"{FQCN} {version}\n\n"
        f"Development build of {base}. It sorts before {base}. "
        f"A requirement of `>={FLOOR}` does not install it once a stable release is on Galaxy.\n\n"
        "This build:\n\n"
        "```bash\n"
        f"ansible-galaxy collection install '{FQCN}:=={version}'\n"
        "```\n\n"
        f"Newest development build of {base}:\n\n"
        "```bash\n"
        f"ansible-galaxy collection install {FQCN} --pre '>={base}-dev,<{base}'\n"
        "```\n"
    )


def emit(channel: str, version: str, tag: str, base: str) -> None:
    print(f"channel={channel}")
    print(f"version={version}")
    print(f"tag={tag}")
    print(f"base={base}")


def self_test() -> None:
    sample = "namespace: patchmon\nname: core\nversion: 2.0.0\n"
    assert field(sample, "version") == "2.0.0"
    assert decide("refs/tags/v2.0.0", "2.0.0", "20261103142922") == (
        "stable",
        "2.0.0",
        "v2.0.0",
    )
    assert decide("refs/heads/main", "2.0.0", "20261103142922") == (
        "dev",
        "2.0.0-dev.20261103142922",
        "v2.0.0-dev.20261103142922",
    )
    assert not newer_than_floor("2.0.0-dev.20261103142922")
    assert newer_than_floor("2.0.1-dev.20261103142922")
    assert replace_version(sample, "2.0.0-dev.20261103142922").splitlines()[2] == (
        "version: 2.0.0-dev.20261103142922"
    )
    try:
        decide("refs/tags/v2.0.1", "2.0.0", "20261103142922")
    except ReleaseError:
        pass
    else:
        raise ReleaseError("mismatched tag was accepted")
    assert decide("refs/tags/v2.0.0-dev.20261103142922", "2.0.0", "20261103142922") == (
        "skip",
        "",
        "",
    )
    print("ok")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--galaxy-yml", type=Path, default=Path("galaxy.yml"))
    parser.add_argument("--ref", default="refs/heads/main")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--require-stable-floor", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    text, namespace, name, base = load_galaxy(args.galaxy_yml)
    timestamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    channel, version, tag = decide(args.ref, base, timestamp)
    if channel == "skip":
        emit(channel, version, tag, base)
        return 0
    if (
        args.require_stable_floor
        and channel == "dev"
        and newer_than_floor(version)
        and not galaxy_has_stable(namespace, name)
    ):
        raise ReleaseError(
            f"Refusing to publish {version}. It satisfies >={FLOOR}, and Galaxy has "
            f"no stable {namespace}.{name} release yet. Tag and publish v{FLOOR} first."
        )
    if args.write:
        args.galaxy_yml.write_text(replace_version(text, version))
    if args.notes is not None:
        args.notes.write_text(release_notes(channel, version, base))
    emit(channel, version, tag, base)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReleaseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

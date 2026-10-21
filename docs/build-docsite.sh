#!/usr/bin/env bash
# Build the patchmon.core Sphinx docsite into built-docs/build/html.
# Requires ansible-core and antsibull-docs on PATH.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [ -z "${ANSIBLE_COLLECTIONS_PATHS:-}${ANSIBLE_COLLECTIONS_PATH:-}" ]; then
  collection_root="${TMPDIR:-/tmp}/patchmon-docs-collections"
  rm -rf "$collection_root"
  mkdir -p "$collection_root/ansible_collections/patchmon"
  ln -s "$root" "$collection_root/ansible_collections/patchmon/core"
  export ANSIBLE_COLLECTIONS_PATHS="$collection_root"
fi

rm -rf built-docs
mkdir -m 700 built-docs
antsibull-docs sphinx-init --use-current --squash-hierarchy --fail-on-error \
  --project "patchmon.core" \
  --title "patchmon.core" \
  --html-short-title "patchmon.core" \
  --copyright "PatchMon contributors" \
  --extra-html-theme-options "documentation_home_url=https://mrjoshuap.github.io/PatchMon-ansible/" \
  patchmon.core --dest-dir built-docs

cat docs/docsite/conf.py.append >> built-docs/conf.py
printf '\nmyst-parser\nsphinxcontrib-mermaid\n' >> built-docs/requirements.txt
python -m pip install -r built-docs/requirements.txt
python docs/docsite/rewrite_markdown.py
./built-docs/build.sh

#!/usr/bin/env bash
# Build the patchmon.core Sphinx docsite into built-docs/build/html.
# Requires ansible-core and antsibull-docs on PATH.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [ -z "${ANSIBLE_COLLECTIONS_PATHS:-}${ANSIBLE_COLLECTIONS_PATH:-}" ]; then
  collection_root="$root/.collections"
  link="$collection_root/ansible_collections/patchmon/core"
  mkdir -p "$(dirname "$link")"
  if [[ -e "$link" && ! -L "$link" ]]; then
    rm -rf "$link"
  fi
  ln -sfn "$root" "$link"
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

# Former sidebar pages. Keep the URLs, and keep them out of the toctree.
html_docsite="$root/built-docs/build/html/docsite"
mkdir -p "$html_docsite"

write_redirect() {
  local dest="$1"
  local target="$2"
  local title="$3"
  cat > "$html_docsite/$dest" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${title}</title>
  <link rel="canonical" href="${target}">
  <meta http-equiv="refresh" content="0; url=${target}">
</head>
<body>
  <p>This page moved to <a href="${target}">${title}</a>.</p>
</body>
</html>
EOF
}

write_redirect readme.html automator_guide.html "Automator guide"
write_redirect quick_start.html "automator_guide.html#chapter-4-first-inventory" "First inventory"
write_redirect troubleshooting.html "automator_guide.html#chapter-8-troubleshooting" "Troubleshooting"
write_redirect permissions.html "automator_guide.html#chapter-3-credentials" "Credentials"
write_redirect migrating_to_2.0.html "automator_guide.html#chapter-9-migrating-from-1-0" "Migrating from 1.0"

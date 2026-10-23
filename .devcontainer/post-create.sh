#!/bin/bash
# Link this checkout as patchmon.core. A previous galaxy install under
# .collections is a real directory and would shadow the working tree.
set -euo pipefail

root="/workspaces/PatchMon-ansible"
collections="${root}/.collections/ansible_collections"
link="${collections}/patchmon/core"

export ANSIBLE_COLLECTIONS_PATH="${ANSIBLE_COLLECTIONS_PATH:-${root}/.collections:/usr/share/ansible/collections}"

add_safe_directory() {
  local dir="$1"
  local existing
  existing="$(sudo git config --system --get-all safe.directory || true)"
  if ! grep -Fxq -- "${dir}" <<< "${existing}"; then
    sudo git config --system --add safe.directory "${dir}"
  fi
}

if [[ -f /tmp/host.gitconfig ]]; then
  existing_include="$(git config --global --get-all include.path || true)"
  if ! grep -Fxq -- /tmp/host.gitconfig <<< "${existing_include}"; then
    git config --global --add include.path /tmp/host.gitconfig
  fi
fi

add_safe_directory "${root}"

mkdir -p "${collections}/patchmon"
if [[ -e "${link}" && ! -L "${link}" ]]; then
  rm -rf "${link}"
fi
ln -sfn "${root}" "${link}"
echo "patchmon.core -> $(readlink -f "${link}")"

echo "ansible:"
ansible --version
echo "ansible-lint:"
ansible-lint --version
echo "pytest:"
pytest --version
ansible-galaxy collection list patchmon.core

# if .env exists, source it
if [[ -f .env ]]; then
  source .env
fi

# Older .env files may set only PATCHMON_SERVER_URL. Derive the enrollment and
# hosts URLs when those overrides are unset. An explicit value still wins.
_patchmon_server="${PATCHMON_SERVER_URL:-}"
_patchmon_server="${_patchmon_server%/}"
if [[ -n "${_patchmon_server}" ]]; then
  _patchmon_enrollment="${_patchmon_server}/api/v1/auto-enrollment"
  _patchmon_api="${_patchmon_server}/api/v1/api/hosts"
  if [[ -n "${PATCHMON_ENROLLMENT_URL:-}" && "${PATCHMON_ENROLLMENT_URL}" != "${_patchmon_enrollment}" ]]; then
    echo "PATCHMON_ENROLLMENT_URL is set. Prefer PATCHMON_SERVER_URL and leave PATCHMON_ENROLLMENT_URL unset."
  fi
  if [[ -n "${PATCHMON_API_URL:-}" && "${PATCHMON_API_URL}" != "${_patchmon_api}" ]]; then
    echo "PATCHMON_API_URL is set. Prefer PATCHMON_SERVER_URL and leave PATCHMON_API_URL unset."
  fi
  export PATCHMON_ENROLLMENT_URL="${PATCHMON_ENROLLMENT_URL:-${_patchmon_enrollment}}"
  export PATCHMON_API_URL="${PATCHMON_API_URL:-${_patchmon_api}}"
fi
unset _patchmon_server _patchmon_enrollment _patchmon_api

# if PATCHMON environment variables are not set, print a message instructing the user to export the environment variables
if [[ -z "${PATCHMON_ENROLLMENT_KEY:-}" || -z "${PATCHMON_ENROLLMENT_SECRET:-}" || -z "${PATCHMON_API_KEY:-}" || -z "${PATCHMON_API_SECRET:-}" || -z "${PATCHMON_SERVER_URL:-}" ]]; then
  echo "Please export the following environment variables:"
  echo "export PATCHMON_ENROLLMENT_KEY"
  echo "export PATCHMON_ENROLLMENT_SECRET"
  echo "export PATCHMON_API_KEY"
  echo "export PATCHMON_API_SECRET"
  echo "export PATCHMON_SERVER_URL"
  echo "Prefer PATCHMON_SERVER_URL. Do not set PATCHMON_ENROLLMENT_URL or PATCHMON_API_URL unless you must override the derived URLs."
  echo "Optional: export PATCHMON_VERIFY_SSL=true"
  echo "Optional lab only: export PATCHMON_VERIFY_SSL=false"
fi

if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install -c .devcontainer/pre-commit-config.yaml --install-hooks
fi

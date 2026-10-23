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

# print a message instructing the user to export the environment variables
echo "Please export the following environment variables:"
echo "export PATCHMON_ENROLLMENT_KEY"
echo "export PATCHMON_ENROLLMENT_SECRET"
echo "export PATCHMON_API_KEY"
echo "export PATCHMON_API_SECRET"
echo "export PATCHMON_SERVER_URL"
echo "export PATCHMON_API_URL"
echo ""
echo "You should then be able to run view your inventory with:"
echo "  ansible-inventory -i examples/patchmon_inventory.yml --list --yaml"

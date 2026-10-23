#!/bin/bash
# Same playbook set as .github/workflows/ci.yml. ansible-lint installs this
# collection under .ansible/collections; point galaxy at that copy.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${root}"

export ANSIBLE_COLLECTIONS_PATH="${root}/.ansible/collections"
mkdir -p "${ANSIBLE_COLLECTIONS_PATH}"
ansible-lint examples/playbooks/*.yml playbooks/*.yml

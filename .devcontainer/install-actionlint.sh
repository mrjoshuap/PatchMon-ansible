#!/bin/bash
# actionlint has no Fedora package. The image build and Checks both run this.
set -euo pipefail

version=1.7.12
arch="$(uname -m)"
case "${arch}" in
  x86_64) asset=linux_amd64 ;;
  aarch64|arm64) asset=linux_arm64 ;;
  *)
    echo "unsupported architecture: ${arch}" >&2
    exit 1
    ;;
esac

tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
curl -fsSL -o "${tmp}" \
  "https://github.com/rhysd/actionlint/releases/download/v${version}/actionlint_${version}_${asset}.tar.gz"

if [[ "$(id -u)" -eq 0 ]]; then
  tar -C /usr/local/bin -xzf "${tmp}" actionlint
else
  sudo tar -C /usr/local/bin -xzf "${tmp}" actionlint
fi

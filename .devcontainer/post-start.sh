#!/bin/bash
# Host Git and SSH files are optional. When they are mounted, commit signing
# uses the forwarded agent socket. Without them, the container still starts.
set -euo pipefail

sock="/run/host-services/ssh-auth.sock"
if [[ -S "${sock}" ]]; then
  sudo chown "$(id -u):$(id -g)" "${sock}"
  sudo chmod 600 "${sock}"
fi

copy_ssh_file() {
  local src="$1"
  local dest="$2"
  local mode="$3"
  if [[ ! -e "${src}" ]]; then
    echo "Missing SSH file: ${src}" >&2
    exit 1
  fi
  if ! cp "${src}" "${dest}" 2>/dev/null; then
    sudo cp "${src}" "${dest}"
  fi
  sudo chown "$(id -u):$(id -g)" "${dest}"
  chmod "${mode}" "${dest}"
}

host_ssh="/tmp/host-ssh"
ssh_files=(
  "${host_ssh}/config"
  "${host_ssh}/id_rsa.pub"
  "${host_ssh}/known_hosts"
)
present=0
for src in "${ssh_files[@]}"; do
  if [[ -e "${src}" ]]; then
    present=$((present + 1))
  fi
done

if [[ "${present}" -eq 0 ]]; then
  echo "No host SSH files at ${host_ssh}; skipping SSH config."
elif [[ "${present}" -ne 3 ]]; then
  echo "Partial host SSH mount under ${host_ssh}. Expected config, id_rsa.pub, and known_hosts together." >&2
  exit 1
else
  ssh_dir="${HOME}/.ssh"
  mkdir -p "${ssh_dir}"
  chmod 700 "${ssh_dir}"

  copy_ssh_file "${host_ssh}/config" "${ssh_dir}/config.host" 600
  # OpenSSH applies the private-key mode check to IdentityFile, including a
  # .pub file used to select the agent key. 0644 is rejected.
  copy_ssh_file "${host_ssh}/id_rsa.pub" "${ssh_dir}/id_rsa.pub" 600
  copy_ssh_file "${host_ssh}/known_hosts" "${ssh_dir}/known_hosts" 600

  cat > "${ssh_dir}/config" <<EOF
# First IdentityAgent wins. The included host config points at the macOS
# 1Password socket, which does not exist in this container.
Host *
    IdentityAgent /run/host-services/ssh-auth.sock

Include ${ssh_dir}/config.host
EOF
  chmod 600 "${ssh_dir}/config"
fi

# The included host gitconfig signs with the macOS op-ssh-sign binary.
# Cursor also injects SSH_AUTH_SOCK pointing at its own empty agent, so this
# signer pins the forwarded socket before ssh-keygen runs. This include is last.
if [[ -f /tmp/host.gitconfig ]]; then
  mkdir -p "${HOME}/.config/git"
  if [[ -f "${host_ssh}/allowed_signers" ]]; then
    copy_ssh_file "${host_ssh}/allowed_signers" "${HOME}/.config/git/allowed_signers" 644
  fi
  cat > "${HOME}/.config/git/ssh-sign" <<'EOF'
#!/bin/sh
export SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock
exec /usr/bin/ssh-keygen "$@"
EOF
  chmod 755 "${HOME}/.config/git/ssh-sign"
  cat > "${HOME}/.config/git/container-signing" <<EOF
[gpg "ssh"]
	program = ${HOME}/.config/git/ssh-sign
	allowedSignersFile = ${HOME}/.config/git/allowed_signers
EOF
  cat > "${HOME}/.gitconfig" <<EOF
[include]
	path = /tmp/host.gitconfig
[include]
	path = ${HOME}/.config/git/container-signing
EOF
else
  echo "No /tmp/host.gitconfig; leaving git config unchanged."
fi

# if .env exists, source it
if [[ -f .env ]]; then
  source .env
fi

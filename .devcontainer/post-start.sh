#!/bin/bash
# The host SSH config selects keys and ports. Docker Desktop forwards the
# 1Password agent on /run/host-services/ssh-auth.sock, which is root-only
# until this chown. IdentityAgent in the host file is the macOS socket path,
# so the container config sets SSH_AUTH_SOCK before including that file.
set -euo pipefail

sock="/run/host-services/ssh-auth.sock"
if [[ -S "${sock}" ]]; then
  sudo chown "$(id -u):$(id -g)" "${sock}"
  sudo chmod 600 "${sock}"
fi

ssh_dir="${HOME}/.ssh"
mkdir -p "${ssh_dir}"
chmod 700 "${ssh_dir}"

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

copy_ssh_file /tmp/host-ssh/config "${ssh_dir}/config.host" 600
# OpenSSH applies the private-key mode check to IdentityFile, including a
# .pub file used to select the agent key. 0644 is rejected.
copy_ssh_file /tmp/host-ssh/id_rsa.pub "${ssh_dir}/id_rsa.pub" 600
copy_ssh_file /tmp/host-ssh/known_hosts "${ssh_dir}/known_hosts" 600

cat > "${ssh_dir}/config" <<EOF
# First IdentityAgent wins. The included host config points at the macOS
# 1Password socket, which does not exist in this container.
Host *
    IdentityAgent /run/host-services/ssh-auth.sock

Include ${ssh_dir}/config.host
EOF
chmod 600 "${ssh_dir}/config"

# The included host gitconfig signs with the macOS op-ssh-sign binary.
# Cursor also injects SSH_AUTH_SOCK pointing at its own empty agent, so this
# signer pins the 1Password socket before ssh-keygen runs. This include is last.
mkdir -p "${HOME}/.config/git"
if [[ -f /tmp/host-ssh/allowed_signers ]]; then
  copy_ssh_file /tmp/host-ssh/allowed_signers "${HOME}/.config/git/allowed_signers" 644
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

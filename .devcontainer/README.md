# patchmon.core dev container

Open this repository on its own. The container is only the collection checkout. It uses `quay.io/mrjoshuap/ee-homelab-workspace:latest` (Ansible, ansible-lint, and pytest). Mounts are Git and SSH only.

## Open

1. On the host, `docker login quay.io` if that image is private. These files must exist, because the container bind-mounts them: `~/.gitconfig`, `~/.ssh/config`, `~/.ssh/id_rsa.pub`, `~/.ssh/known_hosts`, and `~/.config/git/allowed_signers`.
2. On the Mac, the 1Password agent has to be the socket Docker Desktop forwards. If the homelab container already works, that setup is done. Otherwise run `home-mrjoshuap/.devcontainer/enable-1password-agent-for-docker.sh` once, then quit Docker Desktop and open it again.
3. In Cursor, **File → Open Workspace from File** and choose `patchmon-ansible.code-workspace`.
4. Command Palette → **Dev Containers: Reopen in Container**.

`post-create.sh` replaces a galaxy-installed directory at `.collections/ansible_collections/patchmon/core` with a symlink to this checkout, so Ansible loads the working tree. `.collections/` stays gitignored.

SSH and commit signing match the homelab container: `IdentityAgent` is `/run/host-services/ssh-auth.sock`, and the container signer is `/usr/bin/ssh-keygen` with that socket set. Private keys stay in 1Password.

**Rebuild Container** pulls the base image with Buildx. If that fails immediately, Cursor's PATH cannot see `docker-credential-desktop`. The fix is the same host setting as the homelab container (`dev.containers.dockerPath` → `~/.local/bin/docker-with-cred-path`). **Reopen in Container** uses the image already on disk.

Export `PATCHMON_API_URL`, `PATCHMON_API_KEY`, and `PATCHMON_API_SECRET` in the shell when a play or inventory call needs the API.

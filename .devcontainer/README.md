# patchmon.core dev container

Open this repository and reopen it in the dev container. The image builds from `ghcr.io/ansible/community-ansible-dev-tools:latest`. The Dockerfile adds `sudo`, `tree`, `jq`, ShellCheck, `requests`, pre-commit, ruff, and pymarkdown. It creates the `dev` user and sets `HOME=/home/dev`. Ansible, ansible-lint, yamllint, and pytest come from the base image.

## Open

Command Palette → **Dev Containers: Reopen in Container**.

`post-create.sh` replaces a galaxy-installed directory at `.collections/ansible_collections/patchmon/core` with a symlink to this checkout, so Ansible loads the working tree. `.collections/` stays gitignored.

`patchmon-ansible.code-workspace` is a single-folder workspace with the same editor settings as `devcontainer.json`. Opening the repository folder is enough.

## API environment

Copy `.env.template` to `.env` and fill in the values. `post-create.sh` sources `.env` when that file is present, and prints a reminder when any of these are unset:

- `PATCHMON_ENROLLMENT_KEY`
- `PATCHMON_ENROLLMENT_SECRET`
- `PATCHMON_API_KEY`
- `PATCHMON_API_SECRET`
- `PATCHMON_SERVER_URL`

Set `PATCHMON_SERVER_URL` to the instance root, for example `https://patchmon.example.com`. The template derives `PATCHMON_ENROLLMENT_URL` (`/api/v1/auto-enrollment`) and `PATCHMON_API_URL` (`/api/v1/api/hosts`) when those variables are unset. Setting either URL directly overrides the derived value and is discouraged. `post-create.sh` prints a note when an override does not match the URL derived from `PATCHMON_SERVER_URL`.

`PATCHMON_VERIFY_SSL` is optional. `true` is the default. Set `false` only in a lab.

## Optional commit signing

`devcontainer.json` bind-mounts `/run/host-services/ssh-auth.sock` when the host provides that socket. To sign commits with a forwarded agent, also mount:

- `~/.gitconfig` at `/tmp/host.gitconfig`
- `~/.ssh/config`, `~/.ssh/id_rsa.pub`, and `~/.ssh/known_hosts` under `/tmp/host-ssh/`
- `~/.config/git/allowed_signers` at `/tmp/host-ssh/allowed_signers` when you verify signatures

When those files are present, `post-start.sh` copies the SSH files into the container, sets `IdentityAgent` to `/run/host-services/ssh-auth.sock`, and points Git's SSH signer at `/usr/bin/ssh-keygen` with that socket. Private keys stay in the agent. Without the mounts, startup skips SSH config and signing, and the container still opens.

## Checks

`post-create.sh` installs a git hook from `.devcontainer/pre-commit-config.yaml`. Run the same checks by hand with:

```bash
pre-commit run --all-files -c .devcontainer/pre-commit-config.yaml
```

The hook covers:

- file checks from pre-commit-hooks: trailing whitespace, a final newline, YAML and JSON syntax, Python syntax, merge conflicts, large files, case conflicts, symlinks, private keys, and LF line endings
- yamllint, using `.devcontainer/yamllint.yaml` (line length 160, document start optional, `on` allowed as a mapping key)
- pymarkdown, with the heading, line-length, and changelog rules this tree already violates turned off
- ruff `E` and `F` rules for Python 3.9, using `.devcontainer/ruff.toml`. It does not reformat
- ShellCheck at warning severity
- ansible-lint on `examples/playbooks/*.yml` and `playbooks/*.yml`, the same set as CI, when a playbook or role YAML file is committed

`jq` is on `PATH` for inventory and API output. It is not a hook.

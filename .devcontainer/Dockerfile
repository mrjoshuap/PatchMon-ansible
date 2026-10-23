# Thin local layer. The published EE image sets HOME=/home/runner, and the
# dev container tooling drops a containerEnv HOME override. Cursor installs
# as user dev into $HOME/.cursor-server, so HOME has to be set in the image.
FROM ghcr.io/ansible/community-ansible-dev-tools:latest

# update packages and clean cache
RUN dnf update -y \
  && dnf install -y \
    procps-ng \
    sudo \
    tree \
    jq \
    ShellCheck \
  && dnf clean all --enablerepo='*'

# requests is a collection dependency. The others back the git hook in
# .devcontainer/pre-commit-config.yaml. yamllint and ansible-lint are in the base image.
RUN pip3 install \
    requests \
    pre-commit==4.7.0 \
    pymarkdownlnt==0.9.41 \
    ruff==0.17.2

# create dev user
RUN useradd -m dev \
  && echo "dev:dev" | chpasswd \
  && usermod -aG wheel dev \
  && echo "dev ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

ENV HOME=/home/dev
USER dev

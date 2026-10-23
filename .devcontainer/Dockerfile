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
  && dnf clean all --enablerepo='*'

# install requests with pip3
RUN pip3 install requests

# create dev user
RUN useradd -m dev \
  && echo "dev:dev" | chpasswd \
  && usermod -aG wheel dev \
  && echo "dev ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

ENV HOME=/home/dev
USER dev

---
title: Developer guide
description: How to change the patchmon.core collection, run tests, build the docsite, and cut a release.
---

# Developer guide

This book is for people changing this repository. Playbook authors should read the [automator guide](automator-guide.md).

## Table of Contents

- [Chapter 1: Repository map](#chapter-1-repository-map)
- [Chapter 2: Dev container](#chapter-2-dev-container)
- [Chapter 3: Tests and lint](#chapter-3-tests-and-lint)
- [Chapter 4: Where documentation lives](#chapter-4-where-documentation-lives)
- [Chapter 5: Docsite build](#chapter-5-docsite-build)
- [Chapter 6: Cutting a release](#chapter-6-cutting-a-release)

## Chapter 1: Repository map

| Path | What it is |
|------|------------|
| [`galaxy.yml`](../galaxy.yml) | Collection namespace, name, version, and Galaxy metadata |
| [`README.md`](../README.md) | Galaxy doorway. Install, one inventory snippet, and links. The narrative lives in the guides |
| [`plugins/inventory/`](../plugins/inventory/) | `patchmon.core.inventory` |
| [`plugins/modules/`](../plugins/modules/) | `host`, `host_info`, `host_packages`, `host_token` |
| [`plugins/lookup/`](../plugins/lookup/) | `host` and `endpoint` lookups |
| [`plugins/module_utils/`](../plugins/module_utils/) | Shared API client and group-name helpers |
| [`plugins/doc_fragments/`](../plugins/doc_fragments/) | Shared `DOCUMENTATION` for Integration API options |
| [`roles/`](../roles/) | `agent`, `host`, `report_health`, `apply_security_updates`, `apply_all_updates`, `reboot_needed` |
| [`playbooks/`](../playbooks/) | Thin plays for the `agent` and `host` roles |
| [`examples/`](../examples/) | Commented inventory files and copy-paste plays. [`examples/README.md`](../examples/README.md) is the file index |
| [`docs/automator-guide.md`](automator-guide.md) | Source of truth for inventories, credentials, and plays |
| [`docs/docsite/`](docsite/) | Sphinx theme, extra-docs nav, and the Markdown include hook |
| [`tests/unit/`](../tests/unit/) | pytest for the API client, inventory, modules, and lookups |
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | pytest and ansible-lint |
| [`.github/workflows/docs.yml`](../.github/workflows/docs.yml) | Docsite build and GitHub Pages |
| [`.github/workflows/release.yml`](../.github/workflows/release.yml) | Tag build, collection tarball, GitHub Release |
| [`.devcontainer/`](../.devcontainer/) | Dev container image and startup scripts |

## Chapter 2: Dev container

Reopen this repository in the dev container. The image builds from `ghcr.io/ansible/community-ansible-dev-tools:latest`. The Dockerfile adds `sudo`, `tree`, and `requests`, creates the `dev` user, and sets `HOME=/home/dev`. Ansible, ansible-lint, and pytest come from the base image.

Command Palette → **Dev Containers: Reopen in Container**.

`post-create.sh` replaces a galaxy-installed directory at `.collections/ansible_collections/patchmon/core` with a symlink to this checkout, so Ansible loads the working tree. `.collections/` stays gitignored. `pytest` creates that symlink when it is missing.

Copy `.env.template` to `.env` and fill in `PATCHMON_ENROLLMENT_KEY`, `PATCHMON_ENROLLMENT_SECRET`, `PATCHMON_API_KEY`, `PATCHMON_API_SECRET`, and `PATCHMON_SERVER_URL`. `post-create.sh` sources `.env` when that file is present. Set `PATCHMON_SERVER_URL` to the instance root, for example `https://patchmon.example.com`. The template derives the auto-enrollment and hosts URLs when those variables are unset. Setting either URL directly overrides the derived value and is discouraged.

`PATCHMON_VERIFY_SSL` is optional. `true` is the default. Set `false` only in a lab.

Commit signing through a forwarded SSH agent is optional. The checklist is [`.devcontainer/README.md`](../.devcontainer/README.md). Keep that file as the container-open steps. This chapter is the summary.

## Chapter 3: Tests and lint

```bash
pip install -r requirements.txt pytest ansible-lint pre-commit yamllint pymarkdownlnt ruff antsibull-docs
pytest
pre-commit run --all-files -c .devcontainer/pre-commit-config.yaml
antsibull-docs lint-collection-docs --plugin-docs --skip-rstcheck .
```

Unit tests and local Ansible both import this checkout through `.collections`. The pre-commit ansible-lint hook installs this collection under `.ansible/collections` and points galaxy at that copy. It lints the playbook files under `examples/playbooks/` and `playbooks/`.

Pull requests and pushes to `main` run [`.github/workflows/ci.yml`](../.github/workflows/ci.yml), which calls [`.github/workflows/checks.yml`](../.github/workflows/checks.yml). That suite is pytest, the pre-commit config above, and `antsibull-docs` lint. A tagged release runs the same suite before it builds a tarball. A `main` push that does not change `galaxy.yml` `version:` and that touches `galaxy.yml`, `plugins/`, `roles/`, `playbooks/`, or `meta/` publishes `vX.Y.Z-dev.<run id>` as a GitHub prerelease after the suite passes. The Gitea publish workflow creates the same `.collections` link before pytest and sets `ANSIBLE_COLLECTIONS_PATH` to that link.

## Chapter 4: Where documentation lives

Write each fact once.

- Workflows and collection behavior go in the [automator guide](automator-guide.md) or this developer guide.
- Options and return values go in plugin `DOCUMENTATION`, `EXAMPLES`, and `RETURN` strings, and in role READMEs. antsibull builds those pages. Guides link to them. Role READMEs stay short: variables, credentials, one example.
- Runnable plays go in [`examples/playbooks/`](../examples/playbooks/). Guides name the file. They do not fork the YAML.
- PatchMon product behavior stays in the upstream books linked from the automator guide: admin, operator, and API integrations. Do not copy those books into this repository. Chapter 3 of the API integrations guide is the 1.0 inventory plugin.
- The adoption proposal is [`PROPOSAL.md`](../PROPOSAL.md). Paste-ready API gap drafts are [`PATCHMON-FEEDBACK.md`](../PATCHMON-FEEDBACK.md). The changelog is [`CHANGELOG.md`](../CHANGELOG.md). Those are project records, not learning paths.

[`README.md`](../README.md) is the Galaxy readme: description, requirements, install, one inventory snippet, the content table, and links. [`examples/README.md`](../examples/README.md) is a file index.

When a procedure moves, update the guide and delete the old page. Do not leave a second copy in the README or in a parallel RST file.

## Chapter 5: Docsite build

The published site is GitHub Pages for this fork. [`.github/workflows/docs.yml`](../.github/workflows/docs.yml) builds the site and deploys on push to `main`. Pull requests build only. Collection doc lint is in [`.github/workflows/checks.yml`](../.github/workflows/checks.yml), which gates tagged and development releases. The Pages build does not.

Local build:

```bash
bash docs/build-docsite.sh
```

[`docs/build-docsite.sh`](../docs/build-docsite.sh) links this checkout as `patchmon.core`, runs `antsibull-docs sphinx-init`, appends [`docs/docsite/conf.py.append`](docsite/conf.py.append), and builds HTML under `built-docs/build/html`.

[`docs/docsite/rewrite_markdown.py`](docsite/rewrite_markdown.py) rewrites guide and project Markdown into `built-docs/included/` before Sphinx runs. Relative links to the other guide become docsite pages. Links to examples, roles, and playbooks become GitHub blob URLs. The `source-read` hook in `conf.py.append` includes that Markdown into the RST stubs under [`docs/docsite/rst/`](docsite/rst/).

Navigation is [`docs/docsite/extra-docs.yml`](docsite/extra-docs.yml):

- **Guides:** automator guide, developer guide.
- **Project:** changelog, proposal, PatchMon feedback.

antsibull adds the plugin and role index from code and from role READMEs. Mermaid fences in the automator guide render through `sphinxcontrib-mermaid`.

Former URLs (`readme.html`, `quick_start.html`, `troubleshooting.html`, `permissions.html`, `migrating_to_2.0.html`) are meta-refresh pages written after the HTML build. They are not in the sidebar. Each one lands on the matching automator-guide chapter.

Lint plugin and role docs the same way CI does:

```bash
antsibull-docs lint-collection-docs --plugin-docs --skip-rstcheck .
```

## Chapter 6: Cutting a release

The GitHub Release is the annotated tag. Pushing the version bump to `main` does not create it. Tag that commit in the same release.

1. Bump `galaxy.yml` `version`, update `CHANGELOG.md`, commit, and push `main`.
2. Tag that commit. The tag must match `galaxy.yml`, with a `v` prefix. [Release collection](../.github/workflows/release.yml) runs [the shared checks](../.github/workflows/checks.yml) on that commit before it builds.

```bash
git tag -a v2.0.6 -m "patchmon.core 2.0.6"
git push origin v2.0.6
```

3. After the checks pass, that workflow builds the collection tarball and creates the GitHub Release with the `.tar.gz` attached.

A `main` push that does not bump `version:` and that changes collection content publishes a development prerelease `vX.Y.Z-dev.<run id>` from CI. The tarball uses that version. The committed `galaxy.yml` does not. That prerelease is not the stable release. Tags containing `-dev.` do not start the stable release workflow.

v2.0.4 was first tagged on the version-bump commit. That copy of the workflow ran unit tests without the checkout link, and the job failed. The tag was moved to the later commit that creates the link.

You can also run the workflow manually (**Actions → Release collection → Run workflow**) and supply an existing tag such as `v2.0.6`.

The release notes include a link to [Migrating from 1.0](automator-guide.md#chapter-9-migrating-from-1-0) in the automator guide.

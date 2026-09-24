# Design

## Context

This repository (`open-horizon-services.github.io`) is currently empty apart from a bare `README.md`. It will become the GitHub Pages documentation portal for the `open-horizon-services` organization. The site must aggregate per-repo Markdown docs from many independent repos at build time — a fundamentally different model from a single-repo MkDocs site. See `proposal.md - Why` for the motivation.

## Goals / Non-Goals

**Goals:**
- Deploy a publicly accessible MkDocs site at `https://open-horizon-services.github.io`.
- Automatically discover and include docs from all org repos matching `service-`, `utility-`, `skills-`, and `web-` prefixes at build time.
- Group navigation by prefix in the rendered site.
- Support local preview with `mkdocs serve` both natively and inside a Dev Container / GitHub Codespaces.
- Keep downstream repos unmodified — they only need a `/docs` directory.

**Non-Goals:**
- Real-time or webhook-driven updates; the site rebuilds on push to `main` (or manually via `workflow_dispatch`).
- Versioned docs per repo (a future enhancement).
- Private or internal-only repo support (all targeted repos are public).
- Modifying content in downstream repos as part of this change.

## Decisions

### 1. Plugin strategy: `mkdocs-monorepo-plugin` with a generated `mkdocs.yml`

**Choice**: Use [`mkdocs-monorepo-plugin`](https://github.com/backstage/mkdocs-monorepo-plugin) with a Python pre-build script that:
1. Calls the GitHub REST API to list org repos matching each prefix.
2. Checks each repo for a `/docs` directory.
3. Dynamically writes the `nav:` section of `mkdocs.yml` (or a generated `nav.yml` consumed by the main config) and clones/copies each repo's `/docs` into a temporary `_docs/<repo-name>/` staging directory.
4. Runs `mkdocs build` against the assembled layout.

**Alternatives considered**:
- **`mkdocs-awesome-pages-plugin`**: Better for local monorepos with static folder layouts; does not solve the dynamic remote-repo discovery problem on its own. Could pair it with the same pre-build script, but the monorepo plugin's `!include` directive is cleaner for injecting sub-navs.
- **Git submodules**: Would require manually registering every repo and can't auto-discover new ones. Rejected.
- **`mike` + versioned docs**: Adds version management complexity not needed at this stage. Rejected for now.

### 2. Pre-build script: Python, co-located with the workflow

**Choice**: Write a `scripts/build_nav.py` Python script that performs discovery and staging. The GitHub Actions workflow calls this script before `mkdocs build`.

**Rationale**: Keeps the logic testable and runnable locally (`python scripts/build_nav.py` + `mkdocs serve`). Python is already the language of the MkDocs ecosystem, so no additional runtime dependency is introduced.

**Alternative**: Bash script in the workflow YAML — harder to test locally and less readable for contributors new to the project.

### 3. GitHub API authentication: GITHUB_TOKEN + optional PAT secret

**Choice**: The workflow uses the built-in `GITHUB_TOKEN` to push to `gh-pages`. For listing/cloning public org repos, it uses a repo secret `ORG_READ_TOKEN` (a classic PAT with `public_repo` scope) when available; falls back to unauthenticated requests when the secret is absent.

**Rationale**: Keeps the setup frictionless for forks and mirrors while avoiding rate-limit failures on heavily active orgs.

### 4. Staging directory pattern: `_docs/<repo-name>/`

**Choice**: Each discovered repo's `/docs` content is checked out (via shallow clone or the GitHub contents API) into a local `_docs/<repo-name>/` directory. This directory is `.gitignore`'d and cleaned before each build.

**Rationale**: Avoids polluting the working tree with committed docs copies. Shallow clones (`--depth 1`) keep the workflow fast even with many repos.

### 5. Navigation structure: auto-generated, prefix-labeled sections

The generated `nav:` section maps prefix groups to human-readable labels:

```
nav:
  - Home: index.md
  - Services:
      - service-foo: _docs/service-foo/...
  - Utilities:
      - utility-bar: _docs/utility-bar/...
  - Skills:
      - skills-baz: _docs/skills-baz/...
  - Web:
      - web-qux: _docs/web-qux/...
```

Repos with no `/docs` are omitted from the generated nav entirely.

### 6. Dev Container: Python base image with post-create install

**Choice**: Use the official `mcr.microsoft.com/devcontainers/python:3` base image in `.devcontainer/devcontainer.json`. The `postCreateCommand` runs `pip install -r requirements.txt` so all MkDocs dependencies are ready immediately after the container starts. Port `8000` is listed in `forwardPorts` for automatic host-to-container forwarding.

**Token handling**: `ORG_READ_TOKEN` is not baked into the image. Instead, `devcontainer.json` references it via `remoteEnv` from the host environment, and a `.env.example` file documents the required variable. Developers set it in their shell profile or a local `.env` file before opening the container.

**Git credentials**: The devcontainer inherits the host's git config and SSH agent via the default Dev Containers git credential forwarding behaviour, so `scripts/build_nav.py` can clone repos without extra setup.

**Alternative**: A custom `Dockerfile` — more control but adds maintenance overhead for a straightforward Python environment. Rejected in favour of the pre-built image.

### 7. Deployment: `peaceiris/actions-gh-pages` action

**Choice**: Use the well-maintained `peaceiris/actions-gh-pages` GitHub Action to push the MkDocs `site/` output to the `gh-pages` branch.

**Alternative**: `mkdocs gh-deploy` — simpler but requires git credentials wired into the workflow manually. The action handles this more cleanly.

## Risks / Trade-offs

- **API rate limits** → Mitigation: always use `ORG_READ_TOKEN` in CI; document that requirement in `CONTRIBUTING.md`. Unauthenticated fallback is acceptable for small orgs.
- **Build time grows with org size** → Mitigation: shallow clones (`--depth 1`); cache `_docs/` between runs with GitHub Actions cache keyed on a hash of the org repo list. If the org grows very large, add a concurrency limit on the clone loop.
- **Downstream repo docs quality** → Mitigation: the build script validates each `/docs` directory is non-empty and contains at least one `.md` file before including it. Invalid or broken Markdown may still cause MkDocs build errors; the workflow surfaces these as build failures without corrupting the deployed site.
- **`mkdocs.yml` regenerated on every build** → The main `mkdocs.yml` in the repo is a template; the build script writes a resolved `mkdocs_build.yml` that is actually passed to `mkdocs build -f mkdocs_build.yml`. The committed `mkdocs.yml` contains static site settings and serves as the config for `mkdocs serve` locally (with manually staged `_docs/` for development).
- **`_docs/` must be gitignored** → If a contributor accidentally commits staged docs, diffs become very noisy. The `.gitignore` entry and a pre-commit hint in `CONTRIBUTING.md` mitigates this.

## Migration Plan

This is a greenfield deployment; no existing site is being replaced. Rollout steps:

1. Merge this change to `main` — the Actions workflow triggers and deploys for the first time.
2. Confirm the `gh-pages` branch is created and GitHub Pages is configured to serve from it (one-time manual step in repo Settings → Pages).
3. Verify the site is live at `https://open-horizon-services.github.io`.

Rollback: if the deployment introduces a broken site, re-run the previous successful workflow run via `workflow_dispatch` with the last known-good commit SHA, or revert the offending commit to `main`.

## Open Questions

- Should the prefix list be extended at launch (e.g., `example-`, `demo-`)? This can be added to `mkdocs.yml` config after the initial site ships without affecting the architecture.
- Should the `ORG_READ_TOKEN` secret have a name other than `ORG_READ_TOKEN`? The name is configurable in the workflow YAML and can be changed before merge.

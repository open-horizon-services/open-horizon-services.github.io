# Proposal

## Why

The `open-horizon-services` GitHub organization hosts multiple repos (services, utilities, skills, web projects) with no unified documentation portal. Users and contributors have no single place to browse and discover documentation across repos, making onboarding and cross-project navigation difficult. Standing up a GitHub Pages site using MkDocs provides a polished, searchable, automatically-assembled documentation hub driven directly from each repo's existing `/docs` directory.

## What Changes

- Add a new GitHub Pages documentation site at `open-horizon-services.github.io` (this repository).
- Configure MkDocs with the Material theme and a navigation structure that indexes repos by prefix group (`service-*`, `utility-*`, `skills-*`, `web-*`).
- Add a GitHub Actions workflow that:
  - Discovers all organization repos matching the configured prefixes.
  - Clones or fetches each repo's `/docs` content at build time.
  - Assembles a composite MkDocs project and deploys to `gh-pages`.
- Add a `mkdocs.yml` at the repo root with site metadata, plugins (multi-docs/awesome-pages or monorepo), and Material theme configuration.
- Add a top-level `docs/index.md` that serves as the landing page with a grouped repo index.
- Provide a local development workflow (`make serve` or script) so contributors can preview the assembled site locally.
- Add a `.devcontainer/` configuration so contributors can preview the assembled site inside a VS Code Dev Container or GitHub Codespaces without installing any local dependencies.

## Capabilities

### New Capabilities

- `docs-site/configuration`: MkDocs project configuration — `mkdocs.yml`, Material theme, plugins, and site-level navigation skeleton.
- `docs-site/devcontainer`: Dev Container configuration (`.devcontainer/devcontainer.json`) that installs all Python dependencies and forwards the MkDocs port so developers can preview the site in VS Code or GitHub Codespaces without a local Python environment.
- `docs-site/repo-discovery`: Mechanism (GitHub Actions or script) that discovers organization repos by prefix and fetches their `/docs` content into the assembled site.
- `docs-site/deployment`: GitHub Actions CI/CD pipeline that builds and deploys the MkDocs site to GitHub Pages on push.
- `docs-site/landing-page`: Top-level `docs/index.md` landing page that lists and links to all indexed repos, grouped by prefix.

### Modified Capabilities

*(none — this is a greenfield site)*

## Impact

- **This repository** (`open-horizon-services.github.io`): receives `mkdocs.yml`, `docs/`, `.github/workflows/deploy.yml`, `.devcontainer/`, and optional helper scripts.
- **Downstream repos**: no changes required; each repo must maintain a `/docs` directory with valid Markdown for their content to appear. Repos without `/docs` are skipped gracefully.
- **GitHub Pages**: the `gh-pages` branch of this repo will serve the site; GitHub repository Pages settings must target that branch.
- **Dependencies added**: `mkdocs`, `mkdocs-material`, and a multi-repo plugin (e.g. `mkdocs-monorepo-plugin` or `mkdocs-awesome-pages-plugin`) in a `requirements.txt`.
- **GitHub token scope**: the Actions workflow needs a read token (or `GITHUB_TOKEN`) with `contents: read` access to list and clone public organization repos.

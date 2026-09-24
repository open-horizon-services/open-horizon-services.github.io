# Contributing to Open Horizon Services Documentation

Thank you for contributing! This document covers how to develop the documentation portal locally, how to use a Dev Container or GitHub Codespaces, and how to extend the portal's configuration.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Ignored Paths](#ignored-paths)
- [Adding a New Repo Prefix](#adding-a-new-repo-prefix)
- [Dev Container / Codespaces](#dev-container--codespaces)
- [Running Tests](#running-tests)

---

## Prerequisites

- Python 3.9 or later
- `git`
- (Optional) `make`

---

## Local Setup

```bash
# 1. Clone this repository
git clone https://github.com/open-horizon-services/open-horizon-services.github.io
cd open-horizon-services.github.io

# 2. Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set your GitHub token — see Environment Variables below
export ORG_READ_TOKEN=ghp_...

# 5. Stage org repo docs and start the preview server
make serve
# or without Make:
python scripts/build_nav.py
mkdocs serve -f mkdocs_build.yml
```

The site is available at <http://127.0.0.1:8000>.

Other useful Make targets:

| Command       | Description                                           |
|---------------|-------------------------------------------------------|
| `make stage`  | Fetch org repo docs into `_docs/` only                |
| `make serve`  | Stage then start the preview server                   |
| `make dry-run`| Show which repos would be included (no cloning)       |
| `make test`   | Run unit tests                                        |
| `make clean`  | Remove `_docs/`, `site/`, `mkdocs_build.yml`          |

---

## Environment Variables

| Variable        | Required | Description |
|-----------------|----------|-------------|
| `ORG_READ_TOKEN` | Recommended | GitHub Personal Access Token (classic) with `public_repo` scope. Used to authenticate GitHub API calls and avoid rate limits. Falls back to unauthenticated requests when absent, which works for small organizations but may hit the 60 req/hr limit. |

Set `ORG_READ_TOKEN` in your shell profile, or copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env
# Edit .env and set ORG_READ_TOKEN=ghp_...
```

> **Important:** `.env` is listed in `.gitignore`. Never commit a real token.

---

## Ignored Paths

The following paths are generated at build time and are gitignored — do not commit them:

| Path              | Description |
|-------------------|-------------|
| `_docs/`          | Staged documentation cloned from org repos |
| `site/`           | MkDocs HTML build output |
| `mkdocs_build.yml`| Auto-generated MkDocs config with dynamic nav |
| `.env`            | Local environment variables (tokens) |

---

## Adding a New Repo Prefix

The prefix list is configured in `mkdocs.yml` under `extra.repo_prefixes`. No script changes are needed.

1. Open `mkdocs.yml`.
2. Add the new prefix to the `extra.repo_prefixes` list:

   ```yaml
   extra:
     repo_prefixes:
       - service-
       - utility-
       - skills-
       - web-
       - example-    # ← new prefix
   ```

3. Add a human-readable label mapping in `scripts/build_nav.py` under `PREFIX_LABELS`:

   ```python
   PREFIX_LABELS = {
       ...
       "example-": "Examples",
   }
   ```

4. Run `make dry-run` to confirm the new repos are picked up.

---

## Dev Container / Codespaces

You can preview the documentation site without installing any local dependencies using a VS Code Dev Container or GitHub Codespaces.

### VS Code Dev Container

1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. Open this repository in VS Code.
3. When prompted, click **Reopen in Container** (or run `Dev Containers: Reopen in Container` from the command palette).
4. VS Code will build the container and run `pip install -r requirements.txt` automatically.
5. Set `ORG_READ_TOKEN` in your host shell **before** opening the container so it is forwarded:

   ```bash
   export ORG_READ_TOKEN=ghp_...
   code .
   ```

6. Inside the container terminal, run:

   ```bash
   python scripts/build_nav.py --dry-run   # verify discovery works
   make serve                               # stage and serve
   ```

   The site will be forwarded to <http://localhost:8000> in your host browser.

### GitHub Codespaces

1. Open the repository on GitHub and click **Code → Open with Codespaces → New codespace**.
2. Codespaces builds the container automatically and installs all dependencies.
3. Set `ORG_READ_TOKEN` as a [Codespaces secret](https://docs.github.com/en/codespaces/managing-your-codespaces/managing-encrypted-secrets-for-your-codespaces) named `ORG_READ_TOKEN`.
4. In the Codespaces terminal, run:

   ```bash
   make serve
   ```

5. Codespaces will open a forwarded port in the **Ports** tab — click the URL to preview the site.

---

## Running Tests

```bash
make test
# or:
python -m pytest tests/ -v
```

All tests are in `tests/test_build_nav.py` and run offline using mocked HTTP responses.

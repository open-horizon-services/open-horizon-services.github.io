# Tasks

## 1. Repository Scaffolding

- [x] 1.1 Create `.gitignore` at repo root with entries for `_docs/`, `site/`, `mkdocs_build.yml`, and `__pycache__/`; verify `git status` does not track those paths after creation.
- [x] 1.2 Create `requirements.txt` listing `mkdocs`, `mkdocs-material`, `mkdocs-monorepo-plugin`, and `requests`; verify `pip install -r requirements.txt` succeeds in a clean virtual environment.
- [x] 1.3 Update `README.md` with a brief description of the documentation portal, local development instructions (`pip install -r requirements.txt && python scripts/build_nav.py && mkdocs serve`), and the live site URL; verify the README renders correctly on GitHub.

## 2. MkDocs Base Configuration

- [x] 2.1 Create `mkdocs.yml` at repo root with `site_name`, `site_url` (`https://open-horizon-services.github.io`), `theme: name: material`, `plugins: [monorepo]`, and a static `docs_dir: docs`; verify `mkdocs build --config-file mkdocs.yml` exits 0 with an empty `docs/` directory containing only `index.md`.
- [x] 2.2 Create `docs/index.md` with the site introduction paragraph and placeholder grouped-index sections (Services, Utilities, Skills, Web); verify it renders as the home page in `mkdocs serve`.
- [x] 2.3 Add Material theme configuration block to `mkdocs.yml` (palette, features, logo placeholder); verify `mkdocs serve` renders the Material theme without console errors.

## 3. Repo Discovery and Staging Script

- [x] 3.1 Create `scripts/build_nav.py` with a function that calls `https://api.github.com/orgs/open-horizon-services/repos` (paginated) using `ORG_READ_TOKEN` env var when set, otherwise unauthenticated; verify the function returns a list of repo names when run with a valid token.
- [x] 3.2 Add prefix-filtering logic to `scripts/build_nav.py` that accepts the prefix list (`service-`, `utility-`, `skills-`, `web-`) from a config block in `mkdocs.yml` (under a custom `extra:` key) or falls back to hardcoded defaults; verify only repos matching a configured prefix are returned.
- [x] 3.3 Add a `/docs` existence check using the GitHub contents API (`GET /repos/{owner}/{repo}/contents/docs`); verify repos without `/docs` are excluded from the result set and repos with `/docs` are included.
- [x] 3.4 Add shallow-clone staging logic: for each included repo, run `git clone --depth 1 --filter=blob:none --sparse <repo-url> _docs/<repo-name>` and `git sparse-checkout set docs`, then copy `_docs/<repo-name>/docs/` to `_docs/<repo-name>/`; verify `_docs/<repo-name>/` contains the expected Markdown files after staging two test repos locally.
- [x] 3.5 Add nav generation logic: build the YAML `nav:` block grouping repos by prefix label (Services / Utilities / Skills / Web), write it merged with the static `mkdocs.yml` settings into `mkdocs_build.yml`; verify `mkdocs_build.yml` contains the correct nav structure after running `python scripts/build_nav.py` with mock data.
- [x] 3.6 Add a `--dry-run` flag to `scripts/build_nav.py` that prints the discovered repo list and generated nav without cloning or writing files; verify `python scripts/build_nav.py --dry-run` exits 0 and prints expected output.
- [x] 3.7 Write `tests/test_build_nav.py` with unit tests covering: prefix filtering, `/docs` existence check (mocked), and nav YAML generation; verify `python -m pytest tests/` passes with all tests green.

## 4. Local Development Workflow

- [x] 4.1 Create a `Makefile` (or `scripts/serve.sh`) with targets `make stage` (runs `python scripts/build_nav.py`) and `make serve` (runs `mkdocs serve -f mkdocs_build.yml`); verify `make serve` launches the dev server at `http://127.0.0.1:8000` after staging.
- [x] 4.2 Add a `CONTRIBUTING.md` documenting the local setup steps, the `ORG_READ_TOKEN` requirement, the `.gitignore`'d paths, and how to add a new prefix; verify all documented commands run successfully on a clean clone.

## 5. Dev Container

- [x] 5.1 Create `.devcontainer/devcontainer.json` using the `mcr.microsoft.com/devcontainers/python:3` base image with `postCreateCommand: "pip install -r requirements.txt"` and `forwardPorts: [8000]`; verify VS Code offers "Reopen in Container" when the repo is opened.
- [x] 5.2 Add `remoteEnv: { "ORG_READ_TOKEN": "${localEnv:ORG_READ_TOKEN}" }` to `devcontainer.json` so the token is forwarded from the host environment; verify `echo $ORG_READ_TOKEN` inside the container returns the host value.
- [x] 5.3 Create `.env.example` at repo root with a commented `ORG_READ_TOKEN=` entry and instructions; verify the file is present in version control and `.env` itself is listed in `.gitignore`.
- [ ] 5.4 Open the repository in a Dev Container and run `python scripts/build_nav.py --dry-run && mkdocs serve -f mkdocs_build.yml`; verify the site is accessible at `http://localhost:8000` in the host browser via the forwarded port.
- [ ] 5.5 Open the repository in GitHub Codespaces and repeat task 5.4; verify the Codespaces port forwarding surfaces the site in the Codespaces browser preview.
- [x] 5.6 Update `CONTRIBUTING.md` to include a "Dev Container / Codespaces" section describing how to open the project in a container and set `ORG_READ_TOKEN`; verify the documented steps work end-to-end in a fresh container.

## 6. GitHub Actions Deployment Workflow

- [x] 6.1 Create `.github/workflows/deploy.yml` with a `push` trigger on `main` and a `workflow_dispatch` trigger; verify the workflow file parses without errors using `actionlint` or the GitHub Actions linter.
- [x] 6.2 Add a job that checks out the repo, sets up Python, installs `requirements.txt`, runs `python scripts/build_nav.py`, and runs `mkdocs build -f mkdocs_build.yml`; verify a manual `workflow_dispatch` run completes the build step successfully.
- [x] 6.3 Add the `peaceiris/actions-gh-pages` step to deploy `./site` to the `gh-pages` branch using `GITHUB_TOKEN`; verify a `workflow_dispatch` run pushes output to `gh-pages` and the branch is created.
- [x] 6.4 Configure `ORG_READ_TOKEN` as a repository secret (classic PAT, `public_repo` scope) and wire it into the workflow as `env: ORG_READ_TOKEN: ${{ secrets.ORG_READ_TOKEN }}`; verify the discovery step uses the token (check workflow logs show authenticated API calls).
- [x] 6.5 Set workflow `permissions:` to `contents: write` (for `gh-pages` push) and `pages: write`; verify the workflow does not request any broader permissions.

## 7. Integration Verification

- [ ] 7.1 Trigger a full workflow run after enabling GitHub Pages (Settings → Pages → Source: `gh-pages` branch); verify `https://open-horizon-services.github.io` loads the landing page with at least one populated prefix group.
- [ ] 7.2 Confirm a discovered repo with a `/docs` directory appears as a navigable sub-section in the live site; verify clicking its nav entry renders its Markdown content.
- [ ] 7.3 Confirm a discovered repo without a `/docs` directory is absent from the live site navigation; verify the build log shows it was skipped, not errored.
- [ ] 7.4 Trigger `workflow_dispatch` from the GitHub Actions UI (without a code push) and verify the site redeploys successfully.

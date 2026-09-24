# Spec Delta

## Purpose

Defines the Dev Container configuration that lets developers preview the assembled documentation site inside a VS Code Dev Container or GitHub Codespaces without installing Python or any other dependency locally.

## ADDED Requirements

### Requirement: Dev Container configuration file present
A `.devcontainer/devcontainer.json` file SHALL exist in the repository so that VS Code and GitHub Codespaces can automatically detect and offer to open the project in a container.

#### Scenario: VS Code detects the devcontainer
- **WHEN** a developer opens the repository in VS Code with the Dev Containers extension installed
- **THEN** VS Code SHALL prompt to reopen the project in a container using `.devcontainer/devcontainer.json`

#### Scenario: Codespaces detects the devcontainer
- **WHEN** a developer opens the repository in GitHub Codespaces
- **THEN** Codespaces SHALL build and start a container using `.devcontainer/devcontainer.json`

### Requirement: Container installs all Python dependencies automatically
The Dev Container configuration SHALL install all dependencies listed in `requirements.txt` as part of container setup, without requiring any manual `pip install` step from the developer.

#### Scenario: Dependencies available after container start
- **WHEN** the container finishes starting
- **THEN** running `mkdocs --version` inside the container SHALL succeed without errors

### Requirement: MkDocs preview port is forwarded to the host
The Dev Container configuration SHALL forward the MkDocs dev server port (default `8000`) to the host so a developer can access the preview in their local browser.

#### Scenario: Site accessible in host browser after mkdocs serve
- **WHEN** a developer runs `mkdocs serve` (or `make serve`) inside the container
- **THEN** the site SHALL be accessible at `http://localhost:8000` in the developer's host browser

### Requirement: Container provides access to host git credentials for cloning
The Dev Container configuration SHALL configure git credential sharing or mount the host SSH agent so the staging script (`scripts/build_nav.py`) can clone organization repos that require authentication.

#### Scenario: Authenticated clone succeeds inside container
- **WHEN** `scripts/build_nav.py` runs inside the container with `ORG_READ_TOKEN` set
- **THEN** it SHALL successfully clone repos from the organization without prompting for credentials

### Requirement: ORG_READ_TOKEN is available inside the container
The Dev Container configuration SHALL document (via `devcontainer.json` or a companion `.env.example`) how to supply the `ORG_READ_TOKEN` environment variable inside the container so the discovery script can authenticate GitHub API calls.

#### Scenario: Token surfaced to container process
- **WHEN** a developer sets `ORG_READ_TOKEN` in the host environment or a local `.env` file
- **THEN** the variable SHALL be available to processes running inside the container

# Spec Delta

## Purpose

Defines the automated pipeline that builds the MkDocs site and deploys it to GitHub Pages on every push to the main branch.

## ADDED Requirements

### Requirement: GitHub Actions workflow builds and deploys the site
A GitHub Actions workflow SHALL build the MkDocs site and deploy the output to the `gh-pages` branch of this repository on every push to the default branch.

#### Scenario: Push to default branch triggers deployment
- **WHEN** a commit is pushed to the default branch (e.g., `main` or `master`)
- **THEN** the Actions workflow SHALL run, build the site, and push the output to `gh-pages`

#### Scenario: Deployment failure surfaces as a failed workflow run
- **WHEN** the build or deployment step fails (e.g., Python dependency error, MkDocs build error)
- **THEN** the workflow run SHALL exit with a non-zero status and the `gh-pages` branch SHALL NOT be updated with broken output

### Requirement: GitHub Pages serves from the gh-pages branch
The repository's GitHub Pages setting SHALL be configured to serve from the `gh-pages` branch so the deployed site is publicly accessible at `https://open-horizon-services.github.io`.

#### Scenario: Site accessible after first successful deploy
- **WHEN** the workflow completes its first successful deployment
- **THEN** the site SHALL be reachable at `https://open-horizon-services.github.io` without additional manual configuration

### Requirement: Workflow uses least-privilege permissions
The workflow SHALL use the minimum token permissions required: `contents: write` on this repo to push to `gh-pages` and `contents: read` on the organization to list and clone repos.

#### Scenario: GITHUB_TOKEN scoped to required permissions
- **WHEN** the workflow runs in GitHub Actions
- **THEN** it SHALL use `GITHUB_TOKEN` (or an org-scoped PAT stored as a secret) with no broader permissions than `contents: write` for this repo and `contents: read` for cloning org repos

### Requirement: Workflow can be triggered manually
The workflow SHALL support a `workflow_dispatch` trigger so maintainers can rebuild and redeploy the site on demand without a code push.

#### Scenario: Manual trigger via GitHub UI
- **WHEN** a maintainer triggers the workflow from the Actions tab in the GitHub UI
- **THEN** the site SHALL be rebuilt and redeployed exactly as on an automatic push

# Spec Delta

## Purpose

Governs how the build process discovers organization repos by prefix and fetches their `/docs` content into the assembled MkDocs site.

## ADDED Requirements

### Requirement: Repos discovered by prefix from the GitHub organization
The build SHALL discover all repositories in the `open-horizon-services` GitHub organization whose names begin with one of the configured prefixes (`service-`, `utility-`, `skills-`, `web-`).

#### Scenario: Discovery returns repos matching any configured prefix
- **WHEN** the build runs against the organization
- **THEN** every public repo whose name starts with `service-`, `utility-`, `skills-`, or `web-` SHALL appear in the assembled site navigation

#### Scenario: Repos not matching any prefix are excluded
- **WHEN** the build runs against the organization
- **THEN** repos whose names do not begin with a configured prefix SHALL NOT appear in the site

### Requirement: Each repo's /docs content is fetched at build time
For each discovered repo, the build SHALL fetch the contents of its `/docs` directory and make it available to MkDocs as that repo's documentation section.

#### Scenario: Repo with /docs directory included
- **WHEN** a discovered repo contains a `/docs` directory with Markdown files
- **THEN** those files SHALL appear as a sub-section of that repo in the site navigation

#### Scenario: Repo without /docs directory skipped gracefully
- **WHEN** a discovered repo has no `/docs` directory
- **THEN** the build SHALL skip that repo without failing and SHALL NOT produce a broken navigation entry for it

### Requirement: Prefix list is configurable
The set of repo-name prefixes that trigger inclusion SHALL be configurable (e.g., in `mkdocs.yml` or a dedicated config file) without requiring changes to build scripts.

#### Scenario: Adding a new prefix
- **WHEN** a new prefix is added to the configuration
- **THEN** the next build SHALL include repos matching that prefix without any script changes

### Requirement: Build uses GitHub API or equivalent to list repos
The discovery mechanism SHALL use the GitHub REST API (or GitHub CLI) to enumerate organization repos rather than relying on a manually maintained list.

#### Scenario: API token used when available
- **WHEN** a `GITHUB_TOKEN` environment variable or repository secret is present
- **THEN** the discovery SHALL use it to authenticate API requests and avoid rate limiting

#### Scenario: Unauthenticated fallback for public repos
- **WHEN** no token is present
- **THEN** the discovery SHALL still succeed for organizations with only public repos, subject to the GitHub API unauthenticated rate limit

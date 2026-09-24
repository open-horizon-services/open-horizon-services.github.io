# Spec Delta

## Purpose

Defines the MkDocs project configuration that controls site structure, theme, plugins, and navigation for the Open Horizon Services documentation portal.

## ADDED Requirements

### Requirement: MkDocs project file present at repo root
The site SHALL be driven by a `mkdocs.yml` file at the root of the `open-horizon-services.github.io` repository.

#### Scenario: Site name and URL configured
- **WHEN** `mkdocs.yml` is read
- **THEN** `site_name` and `site_url` SHALL be set to values identifying the Open Horizon Services documentation portal

#### Scenario: Material theme selected
- **WHEN** `mkdocs.yml` is read
- **THEN** the `theme.name` field SHALL be `material`

### Requirement: Multi-repo plugin configured
The site SHALL use a plugin that supports pulling documentation from multiple source directories (such as `mkdocs-monorepo-plugin`) so that each discovered repo's `/docs` content can be included as a sub-section.

#### Scenario: Plugin declared in mkdocs.yml
- **WHEN** `mkdocs.yml` is read
- **THEN** the `plugins` list SHALL include the chosen multi-repo plugin with any required configuration

#### Scenario: Python requirements file captures all dependencies
- **WHEN** `requirements.txt` is read
- **THEN** it SHALL list `mkdocs`, `mkdocs-material`, and the chosen multi-repo plugin at pinned or minimum versions

### Requirement: Repo prefix groups reflected in top-level navigation
The navigation SHALL group repos under labelled sections corresponding to each configured prefix (`service-`, `utility-`, `skills-`, `web-`).

#### Scenario: Navigation grouping in built site
- **WHEN** the site is built with repos present for at least two different prefix groups
- **THEN** the top-level navigation SHALL contain one section per prefix group, each containing only repos whose names match that prefix

### Requirement: Configuration supports local preview
The site configuration SHALL be runnable locally with `mkdocs serve` so contributors can preview the assembled site before pushing.

#### Scenario: Local serve succeeds
- **WHEN** a contributor runs `mkdocs serve` in the repo root with dependencies installed
- **THEN** the site SHALL start at `http://127.0.0.1:8000` without errors

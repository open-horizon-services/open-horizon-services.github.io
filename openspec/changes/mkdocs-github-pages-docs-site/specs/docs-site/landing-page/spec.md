# Spec Delta

## Purpose

Defines the content and structure of the site's home page, which serves as a navigable index of all discovered repos grouped by prefix.

## ADDED Requirements

### Requirement: Landing page exists at docs/index.md
A `docs/index.md` file SHALL exist in this repository and SHALL serve as the MkDocs home page for the site.

#### Scenario: Home page renders as site root
- **WHEN** a visitor navigates to `https://open-horizon-services.github.io`
- **THEN** the content of `docs/index.md` SHALL be displayed as the home page

### Requirement: Landing page lists repos grouped by prefix
The landing page SHALL present a grouped index of all discovered organization repos, with one section per prefix group.

#### Scenario: Each prefix group has its own section
- **WHEN** the landing page is rendered
- **THEN** repos beginning with `service-` SHALL appear under a "Services" section, `utility-` under "Utilities", `skills-` under "Skills", and `web-` under "Web" (or equivalent human-readable labels)

#### Scenario: Each repo entry links to its documentation section
- **WHEN** a visitor clicks a repo name on the landing page
- **THEN** they SHALL be taken to that repo's documentation sub-section within the site

#### Scenario: Repo without /docs is omitted from the index
- **WHEN** a repo matching a prefix has no `/docs` directory
- **THEN** it SHALL NOT appear as a link on the landing page

### Requirement: Landing page includes a brief site description
The landing page SHALL include at least one introductory paragraph describing the purpose of the documentation portal and the Open Horizon Services organization.

#### Scenario: Description present on page load
- **WHEN** the landing page is rendered
- **THEN** it SHALL contain at least one sentence explaining what the portal is and who it is for

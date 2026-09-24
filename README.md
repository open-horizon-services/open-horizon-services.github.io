# open-horizon-services.github.io

Documentation portal for the [Open Horizon Services](https://github.com/open-horizon-services) organization.

This site aggregates documentation from all organization repositories that match the configured prefixes (`service-*`, `utility-*`, `skills-*`, `web-*`). Each repo's `/docs` directory is automatically discovered and included at build time.

**Live site:** <https://open-horizon-services.github.io>

---

## Local Development

### Prerequisites

- Python 3.9+
- Git

### Setup

```bash
# Clone the repo
git clone https://github.com/open-horizon-services/open-horizon-services.github.io
cd open-horizon-services.github.io

# Install dependencies
pip install -r requirements.txt

# (Optional) set your GitHub token to avoid API rate limits
export ORG_READ_TOKEN=ghp_...

# Stage docs from org repos and start the preview server
python scripts/build_nav.py
mkdocs serve -f mkdocs_build.yml
```

The site will be available at <http://127.0.0.1:8000>.

### Using Make

```bash
make stage   # fetch org repo docs into _docs/
make serve   # build mkdocs_build.yml and start mkdocs serve
```

### Dev Container / GitHub Codespaces

Open this repository in VS Code with the **Dev Containers** extension or in **GitHub Codespaces** — the container will install all dependencies automatically. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines, how to add new repo prefixes, and how to preview the site locally or in a container.

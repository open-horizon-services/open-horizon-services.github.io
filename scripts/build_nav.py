#!/usr/bin/env python3
"""
build_nav.py — Discovers org repos by prefix, stages their /docs content,
and writes mkdocs_build.yml ready for `mkdocs build -f mkdocs_build.yml`.

Usage:
    python scripts/build_nav.py [--dry-run]

Environment:
    ORG_READ_TOKEN   GitHub PAT with public_repo scope (optional but recommended)

The prefix list is read from mkdocs.yml `extra.repo_prefixes`.
Defaults to ["service-", "utility-", "skills-", "web-"] when not set.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
ORG = "open-horizon-services"
MKDOCS_TEMPLATE = "mkdocs.yml"
MKDOCS_BUILD = "mkdocs_build.yml"
DOCS_STAGING_DIR = "docs/_repos"
DEFAULT_PREFIXES = ["service-", "utility-", "skills-", "web-"]

PREFIX_LABELS = {
    "service-": "Services",
    "utility-": "Utilities",
    "skills-": "Skills",
    "web-": "Web",
}


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    token = os.environ.get("ORG_READ_TOKEN", "")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def list_org_repos(org: str = ORG) -> list[dict]:
    """Return all public repos in *org* via the GitHub REST API (paginated)."""
    repos: list[dict] = []
    url: Optional[str] = f"{GITHUB_API}/orgs/{org}/repos?type=public&per_page=100"
    while url:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        repos.extend(resp.json())
        # Follow Link header for next page
        link = resp.headers.get("Link", "")
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    return repos


def get_repo_docs_source(repo_name: str, org: str = ORG) -> Optional[str]:
    """
    Return how docs should be sourced for this repo:
      "docs"   — repo has a /docs directory
      "readme" — no /docs, but a README.md exists at root
      None     — nothing usable found
    """
    url_docs = f"{GITHUB_API}/repos/{org}/{repo_name}/contents/docs"
    if requests.get(url_docs, headers=_headers(), timeout=30).status_code == 200:
        return "docs"
    url_readme = f"{GITHUB_API}/repos/{org}/{repo_name}/contents/README.md"
    if requests.get(url_readme, headers=_headers(), timeout=30).status_code == 200:
        return "readme"
    return None


# ---------------------------------------------------------------------------
# Prefix filtering
# ---------------------------------------------------------------------------

def load_prefixes(mkdocs_path: str = MKDOCS_TEMPLATE) -> list[str]:
    """Read prefix list from mkdocs.yml extra.repo_prefixes, or use defaults."""
    try:
        with open(mkdocs_path) as f:
            cfg = yaml.safe_load(f)
        prefixes = cfg.get("extra", {}).get("repo_prefixes", None)
        if isinstance(prefixes, list) and prefixes:
            return [str(p) for p in prefixes]
    except (OSError, yaml.YAMLError):
        pass
    return list(DEFAULT_PREFIXES)


def filter_by_prefix(repos: list[dict], prefixes: list[str]) -> list[dict]:
    """Return only repos whose names start with one of *prefixes*."""
    return [r for r in repos if any(r["name"].startswith(p) for p in prefixes)]


# ---------------------------------------------------------------------------
# Staging
# ---------------------------------------------------------------------------

def _linked_md_files(readme_text: str) -> list[str]:
    """
    Parse a README and return relative paths to locally linked .md files.
    Matches [label](path) where path is a relative .md (no scheme, no leading /).
    """
    linked = []
    for path in re.findall(r'\[(?:[^\]]*)\]\(([^)]+)\)', readme_text):
        path = path.split("#")[0].strip()   # strip anchors and whitespace
        if path and not path.startswith(("http://", "https://", "/")) and path.lower().endswith(".md"):
            linked.append(path)
    return linked


def stage_repo(
    repo: dict,
    source: str = "docs",
    staging_root: str = DOCS_STAGING_DIR,
    dry_run: bool = False,
) -> Optional[str]:
    """
    Stage a repo's documentation into docs/_repos/<repo-name>/.

    source="docs"   — sparse-clone the /docs tree (original behaviour)
    source="readme" — sparse-clone README.md plus any locally linked .md files

    Returns the staging path on success, None on failure.
    """
    name = repo["name"]
    clone_url = repo["clone_url"]
    dest = Path(staging_root) / name

    if dry_run:
        print(f"  [dry-run] would clone {clone_url} ({source}) → {dest}/")
        return str(dest)

    # Clean previous staging
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    if source == "docs":
        return _stage_docs(repo, dest)
    else:
        return _stage_readme(repo, dest)


def _clone_sparse(clone_url: str, dest: Path, paths: list[str]) -> bool:
    """Shallow sparse-clone and check out the given path list. Returns True on success."""
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none",
             "--sparse", "--no-local", clone_url, str(dest)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set"] + paths,
            cwd=str(dest), check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"  ⚠ clone failed for {dest.name}: {exc.stderr.decode().strip()}",
              file=sys.stderr)
        return False


def _stage_docs(repo: dict, dest: Path) -> Optional[str]:
    """Sparse-clone /docs and promote its contents to dest/."""
    name = repo["name"]
    if not _clone_sparse(repo["clone_url"], dest, ["docs"]):
        shutil.rmtree(dest, ignore_errors=True)
        return None

    docs_sub = dest / "docs"
    if not docs_sub.is_dir():
        print(f"  ⚠ no docs/ found after clone for {name}", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    tmp = dest.parent / f"_tmp_{name}"
    shutil.copytree(str(docs_sub), str(tmp))
    shutil.rmtree(dest)
    tmp.rename(dest)

    if not list(dest.rglob("*.md")):
        print(f"  ⚠ no .md files in docs/ for {name}, skipping", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    return str(dest)


def _stage_readme(repo: dict, dest: Path) -> Optional[str]:
    """
    Shallow-clone the repo in full (depth=1), then keep only README.md and
    any locally linked .md files — everything else is deleted.
    A full shallow clone is used instead of sparse-checkout because
    sparse patterns for specific filenames require cone mode which varies
    across git versions and fails on plain filenames like 'README.md'.
    """
    name = repo["name"]
    clone_url = repo["clone_url"]

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--no-local", clone_url, str(dest)],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  ⚠ clone failed for {name}: {exc.stderr.decode().strip()}", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    # Remove .git immediately — we don't need history
    git_dir = dest / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    # Find README.md (case-insensitive)
    readme_path = dest / "README.md"
    if not readme_path.exists():
        matches = list(dest.glob("[Rr][Ee][Aa][Dd][Mm][Ee].md"))
        readme_path = matches[0] if matches else None

    if readme_path is None:
        print(f"  ⚠ no README.md found for {name}, skipping", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    # Determine which .md files to keep: README + locally linked files
    readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
    linked = set(_linked_md_files(readme_text))
    keep = {readme_path.name} | linked

    # Delete everything that isn't a kept .md file or its parent directory tree
    # Strategy: collect absolute paths to keep, delete all other files
    keep_abs = set()
    for k in keep:
        keep_abs.add((dest / k).resolve())

    for f in list(dest.rglob("*")):
        if f.is_file() and f.resolve() not in keep_abs:
            f.unlink()

    # Remove empty directories left behind
    for d in sorted(dest.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()  # only succeeds if empty
            except OSError:
                pass

    if not list(dest.rglob("*.md")):
        print(f"  ⚠ no .md files for {name} after filtering, skipping", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    return str(dest)


# ---------------------------------------------------------------------------
# Navigation generation
# ---------------------------------------------------------------------------

def build_nav(
    staged: dict[str, str],
    prefixes: list[str],
) -> list:
    """
    Build the MkDocs nav list.
    staged: {repo_name: staging_path}
    Returns a list suitable for the nav: key in mkdocs_build.yml.
    """
    nav: list = [{"Home": "index.md"}]

    # Group repos by their matched prefix, preserving prefix order
    groups: dict[str, list] = {p: [] for p in prefixes}
    for repo_name, path in sorted(staged.items()):
        for prefix in prefixes:
            if repo_name.startswith(prefix):
                # Collect all .md files relative to the staging dir
                staging_path = Path(path)
                md_files = sorted(staging_path.rglob("*.md"))
                if md_files:
                    # Build sub-nav entries relative to docs_dir (docs/)
                    sub_nav = []
                    for md in md_files:
                        rel = md.relative_to(staging_path)
                        entry_path = f"_repos/{repo_name}/{rel}"
                        # Use stem for simple single files, relative path for sub-dirs
                        if len(md_files) == 1:
                            label = md.stem.replace("-", " ").replace("_", " ").title()
                        else:
                            label = str(rel)
                        sub_nav.append({label: entry_path})
                    groups[prefix].append({repo_name: sub_nav})
                break

    for prefix in prefixes:
        label = PREFIX_LABELS.get(prefix, prefix.rstrip("-").title() + "s")
        entries = groups[prefix]
        if entries:
            nav.append({label: entries})

    return nav


# ---------------------------------------------------------------------------
# mkdocs_build.yml generation
# ---------------------------------------------------------------------------

def write_build_config(
    nav: list,
    template_path: str = MKDOCS_TEMPLATE,
    output_path: str = MKDOCS_BUILD,
    staging_root: str = DOCS_STAGING_DIR,
    dry_run: bool = False,
) -> None:
    """
    Merge nav into the template mkdocs.yml and write mkdocs_build.yml.
    Staged repo docs live inside docs/_repos/, so docs_dir stays as 'docs'
    and nav paths are relative to that directory.
    """
    with open(template_path) as f:
        cfg = yaml.safe_load(f)

    # Override nav with generated structure
    cfg["nav"] = nav

    # docs_dir remains 'docs' — staged content is inside docs/_repos/
    # so MkDocs can find everything without any special plugin.
    cfg["docs_dir"] = "docs"

    if dry_run:
        print("\n--- Generated nav (dry-run) ---")
        print(yaml.dump({"nav": nav}, default_flow_style=False, allow_unicode=True))
        return

    with open(output_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"✓ Written {output_path}")


# ---------------------------------------------------------------------------
# Home page generation
# ---------------------------------------------------------------------------

INDEX_PAGE = "docs/index.md"

def write_index_page(
    nav: list,
    output_path: str = INDEX_PAGE,
    dry_run: bool = False,
) -> None:
    """
    Rewrite docs/index.md with a grouped repo index derived from the nav.
    Each prefix group becomes a section; each repo becomes a link.
    """
    lines = [
        "# Open Horizon Services Documentation",
        "",
        "Welcome to the unified documentation portal for the "
        "[Open Horizon Services](https://github.com/open-horizon-services) organization.",
        "",
        "This portal automatically aggregates documentation from all organization "
        "repositories. Browse by category below, or use the navigation sidebar and "
        "search bar to find specific topics.",
        "",
        "---",
        "",
    ]

    # nav[0] is {"Home": "index.md"} — skip it
    for section in nav[1:]:
        for group_label, repos in section.items():
            lines.append(f"## {group_label}")
            lines.append("")
            for repo_entry in repos:
                for repo_name, sub_nav in repo_entry.items():
                    # Link to the first page in the sub-nav
                    first_path = list(sub_nav[0].values())[0] if sub_nav else "#"
                    display = repo_name
                    lines.append(f"- [{display}]({first_path})")
            lines.append("")
            lines.append("---")
            lines.append("")

    lines.append(
        '!!! tip "Contributing Documentation"\n'
        "    To have your repository's documentation included here, add a `/docs` "
        "directory with Markdown files to your repository. The portal rebuilds "
        "automatically on each push."
    )

    content = "\n".join(lines) + "\n"

    if dry_run:
        print("\n--- Generated index.md (dry-run, first 20 lines) ---")
        for line in lines[:20]:
            print(line)
        return

    with open(output_path, "w") as f:
        f.write(content)
    print(f"✓ Written {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Stage org repo docs and generate mkdocs_build.yml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discovered repos and nav without cloning or writing files",
    )
    parser.add_argument(
        "--org",
        default=ORG,
        help=f"GitHub organization name (default: {ORG})",
    )
    args = parser.parse_args()

    prefixes = load_prefixes()
    print(f"Prefixes: {prefixes}")

    print(f"Fetching repo list for {args.org}…")
    try:
        all_repos = list_org_repos(args.org)
    except requests.HTTPError as exc:
        print(f"Error fetching repos: {exc}", file=sys.stderr)
        sys.exit(1)

    matched = filter_by_prefix(all_repos, prefixes)
    print(f"Matched {len(matched)} repos (from {len(all_repos)} total)")

    # Determine docs source for each matched repo
    print("Checking docs source…")
    repo_sources: list[tuple[dict, str]] = []  # (repo, source)
    for repo in matched:
        name = repo["name"]
        if args.dry_run:
            print(f"  [dry-run] would check {name}")
            repo_sources.append((repo, "docs"))  # assume docs for dry-run nav
        else:
            src = get_repo_docs_source(name, args.org)
            if src == "docs":
                print(f"  ✓ {name} (docs/)")
            elif src == "readme":
                print(f"  ✓ {name} (README.md fallback)")
            else:
                print(f"  – {name} (nothing to include, skipping)")
            if src:
                repo_sources.append((repo, src))

    print(f"\n{len(repo_sources)} repos will be staged")

    # Stage docs
    staged: dict[str, str] = {}
    if not args.dry_run:
        staging_root = Path(DOCS_STAGING_DIR)
        staging_root.mkdir(exist_ok=True)

    print("\nStaging docs…")
    for repo, src in repo_sources:
        name = repo["name"]
        path = stage_repo(repo, source=src, dry_run=args.dry_run)
        if path:
            staged[name] = path
            if not args.dry_run:
                print(f"  ✓ staged {name} ({src})")
        else:
            print(f"  – {name} skipped")

    # Build nav — dry-run uses a synthetic path so build_nav can rglob; use
    # the actual staging path pattern so nav paths are still correct.
    nav = build_nav(
        staged if not args.dry_run
        else {r["name"]: f"{DOCS_STAGING_DIR}/{r['name']}" for r in [rs[0] for rs in repo_sources]},
        prefixes,
    )

    # Write config and regenerate home page index
    write_build_config(nav, dry_run=args.dry_run)
    write_index_page(nav, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\nDone. Run: mkdocs serve -f {MKDOCS_BUILD}")


if __name__ == "__main__":
    main()

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


def has_docs_dir(repo_name: str, org: str = ORG) -> bool:
    """Return True if *repo_name* has a /docs directory."""
    url = f"{GITHUB_API}/repos/{org}/{repo_name}/contents/docs"
    resp = requests.get(url, headers=_headers(), timeout=30)
    return resp.status_code == 200


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

def stage_repo(repo: dict, staging_root: str = DOCS_STAGING_DIR, dry_run: bool = False) -> Optional[str]:
    """
    Shallow-clone the repo's /docs directory into docs/_repos/<repo-name>/.
    Returns the staging path on success, None if /docs is absent or clone fails.
    """
    name = repo["name"]
    clone_url = repo["clone_url"]
    dest = Path(staging_root) / name

    if dry_run:
        print(f"  [dry-run] would clone {clone_url} → {dest}/")
        return str(dest)

    # Clean previous staging
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Shallow sparse clone — only the docs/ tree
    try:
        subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--filter=blob:none",
                "--sparse",
                "--no-local",
                clone_url,
                str(dest),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set", "docs"],
            cwd=str(dest),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  ⚠ clone failed for {name}: {exc.stderr.decode().strip()}", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    # Flatten: move docs/* up one level so _docs/<name>/<file>.md
    docs_sub = dest / "docs"
    if not docs_sub.is_dir():
        print(f"  ⚠ no docs/ found after clone for {name}", file=sys.stderr)
        shutil.rmtree(dest, ignore_errors=True)
        return None

    # Move contents out of the docs/ subdirectory
    for item in docs_sub.iterdir():
        shutil.move(str(item), str(dest / item.name))
    docs_sub.rmdir()

    # Verify at least one markdown file exists
    md_files = list(dest.rglob("*.md"))
    if not md_files:
        print(f"  ⚠ no .md files found for {name}, skipping", file=sys.stderr)
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

    # Check /docs existence
    print("Checking /docs availability…")
    with_docs = []
    for repo in matched:
        name = repo["name"]
        if args.dry_run:
            print(f"  [dry-run] would check {name}/docs")
            with_docs.append(repo)
        elif has_docs_dir(name, args.org):
            print(f"  ✓ {name}")
            with_docs.append(repo)
        else:
            print(f"  – {name} (no /docs, skipping)")

    print(f"\n{len(with_docs)} repos have /docs")

    # Stage docs
    staged: dict[str, str] = {}
    if not args.dry_run:
        staging_root = Path(DOCS_STAGING_DIR)
        staging_root.mkdir(exist_ok=True)

    print("\nStaging docs…")
    for repo in with_docs:
        name = repo["name"]
        path = stage_repo(repo, dry_run=args.dry_run)
        if path:
            staged[name] = path
            if not args.dry_run:
                print(f"  ✓ staged {name}")
        else:
            print(f"  – {name} skipped")

    # Build nav — dry-run uses a synthetic path so build_nav can rglob; use
    # the actual staging path pattern so nav paths are still correct.
    nav = build_nav(
        staged if not args.dry_run
        else {r["name"]: f"{DOCS_STAGING_DIR}/{r['name']}" for r in with_docs},
        prefixes,
    )

    # Write config
    write_build_config(nav, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\nDone. Run: mkdocs serve -f {MKDOCS_BUILD}")


if __name__ == "__main__":
    main()

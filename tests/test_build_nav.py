"""
tests/test_build_nav.py — Unit tests for scripts/build_nav.py
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import build_nav  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_REPOS = [
    {"name": "service-foo", "clone_url": "https://github.com/org/service-foo.git"},
    {"name": "service-bar", "clone_url": "https://github.com/org/service-bar.git"},
    {"name": "utility-baz", "clone_url": "https://github.com/org/utility-baz.git"},
    {"name": "skills-qux", "clone_url": "https://github.com/org/skills-qux.git"},
    {"name": "web-portal", "clone_url": "https://github.com/org/web-portal.git"},
    {"name": "unrelated-repo", "clone_url": "https://github.com/org/unrelated-repo.git"},
    {"name": "open-horizon-services.github.io", "clone_url": "https://..."},
]


# ---------------------------------------------------------------------------
# Prefix filtering
# ---------------------------------------------------------------------------

class TestFilterByPrefix:
    def test_matches_all_configured_prefixes(self):
        prefixes = ["service-", "utility-", "skills-", "web-"]
        result = build_nav.filter_by_prefix(SAMPLE_REPOS, prefixes)
        names = [r["name"] for r in result]
        assert "service-foo" in names
        assert "service-bar" in names
        assert "utility-baz" in names
        assert "skills-qux" in names
        assert "web-portal" in names

    def test_excludes_non_matching_repos(self):
        prefixes = ["service-", "utility-", "skills-", "web-"]
        result = build_nav.filter_by_prefix(SAMPLE_REPOS, prefixes)
        names = [r["name"] for r in result]
        assert "unrelated-repo" not in names
        assert "open-horizon-services.github.io" not in names

    def test_empty_prefix_list_returns_nothing(self):
        result = build_nav.filter_by_prefix(SAMPLE_REPOS, [])
        assert result == []

    def test_single_prefix_filters_correctly(self):
        result = build_nav.filter_by_prefix(SAMPLE_REPOS, ["service-"])
        names = [r["name"] for r in result]
        assert names == ["service-foo", "service-bar"]

    def test_empty_repo_list_returns_empty(self):
        result = build_nav.filter_by_prefix([], ["service-"])
        assert result == []


# ---------------------------------------------------------------------------
# Docs source detection (mocked)
# ---------------------------------------------------------------------------

class TestGetRepoDocsSource:
    def _mock_get(self, docs_status: int, readme_status: int):
        """Return a side_effect function that returns different codes per URL."""
        def side_effect(url, **kwargs):
            resp = MagicMock()
            if "/contents/docs" in url:
                resp.status_code = docs_status
            else:
                resp.status_code = readme_status
            return resp
        return side_effect

    def test_returns_docs_when_docs_dir_exists(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(200, 404)):
            assert build_nav.get_repo_docs_source("service-foo") == "docs"

    def test_returns_readme_when_no_docs_dir(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(404, 200)):
            assert build_nav.get_repo_docs_source("service-foo") == "readme"

    def test_returns_none_when_neither_exists(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(404, 404)):
            assert build_nav.get_repo_docs_source("service-foo") is None

    def test_docs_takes_priority_over_readme(self):
        # Even if README also exists, docs/ wins
        with patch("build_nav.requests.get", side_effect=self._mock_get(200, 200)):
            assert build_nav.get_repo_docs_source("service-foo") == "docs"

    def test_correct_docs_url_called(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(200, 404)) as mock_get:
            build_nav.get_repo_docs_source("service-foo", "my-org")
            first_url = mock_get.call_args_list[0][0][0]
            assert "my-org/service-foo/contents/docs" in first_url


# ---------------------------------------------------------------------------
# Linked md file parser
# ---------------------------------------------------------------------------

class TestLinkedMdFiles:
    def test_finds_relative_md_links(self):
        text = "See [setup](SETUP.md) and [guide](docs/guide.md) for details."
        assert build_nav._linked_md_files(text) == ["SETUP.md", "docs/guide.md"]

    def test_ignores_http_links(self):
        text = "[external](https://example.com/README.md)"
        assert build_nav._linked_md_files(text) == []

    def test_ignores_absolute_paths(self):
        text = "[abs](/docs/README.md)"
        assert build_nav._linked_md_files(text) == []

    def test_ignores_non_md_links(self):
        text = "[image](./logo.png) [script](run.sh)"
        assert build_nav._linked_md_files(text) == []

    def test_strips_anchors(self):
        text = "[section](CONTRIBUTING.md#setup)"
        assert build_nav._linked_md_files(text) == ["CONTRIBUTING.md"]

    def test_empty_readme(self):
        assert build_nav._linked_md_files("") == []


# ---------------------------------------------------------------------------
# Nav generation
# ---------------------------------------------------------------------------

class TestBuildNav:
    def _make_staged(self, tmp_path: Path, repo_name: str, files: list[str]) -> str:
        """Create a staging directory with given markdown files."""
        repo_dir = tmp_path / repo_name
        repo_dir.mkdir(parents=True)
        for f in files:
            p = repo_dir / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"# {f}\n")
        return str(repo_dir)

    def test_home_always_first(self, tmp_path):
        staged = {}
        nav = build_nav.build_nav(staged, ["service-"])
        assert nav[0] == {"Home": "index.md"}

    def test_prefix_group_present_when_repos_exist(self, tmp_path):
        staged = {
            "service-foo": self._make_staged(tmp_path, "service-foo", ["index.md"]),
        }
        nav = build_nav.build_nav(staged, ["service-", "utility-"])
        labels = [list(item.keys())[0] for item in nav]
        assert "Services" in labels

    def test_empty_prefix_group_omitted(self, tmp_path):
        staged = {
            "service-foo": self._make_staged(tmp_path, "service-foo", ["index.md"]),
        }
        nav = build_nav.build_nav(staged, ["service-", "utility-"])
        labels = [list(item.keys())[0] for item in nav]
        assert "Utilities" not in labels

    def test_all_four_groups_present(self, tmp_path):
        staged = {
            "service-foo": self._make_staged(tmp_path, "service-foo", ["index.md"]),
            "utility-bar": self._make_staged(tmp_path, "utility-bar", ["index.md"]),
            "skills-baz": self._make_staged(tmp_path, "skills-baz", ["index.md"]),
            "web-portal": self._make_staged(tmp_path, "web-portal", ["index.md"]),
        }
        nav = build_nav.build_nav(staged, ["service-", "utility-", "skills-", "web-"])
        labels = [list(item.keys())[0] for item in nav]
        assert "Services" in labels
        assert "Utilities" in labels
        assert "Skills" in labels
        assert "Web" in labels

    def test_repo_entry_path_references_staging_dir(self, tmp_path):
        staged = {
            "service-foo": self._make_staged(tmp_path, "service-foo", ["index.md"]),
        }
        # Patch DOCS_STAGING_DIR to use tmp_path so rglob works
        original = build_nav.DOCS_STAGING_DIR
        build_nav.DOCS_STAGING_DIR = str(tmp_path)
        try:
            nav = build_nav.build_nav(staged, ["service-"])
        finally:
            build_nav.DOCS_STAGING_DIR = original
        # Find the Services section entries
        services = next(item["Services"] for item in nav if "Services" in item)
        foo_entry = next(item for item in services if "service-foo" in item)
        sub_nav = foo_entry["service-foo"]
        assert any(str(tmp_path) in list(e.values())[0] or "index.md" in list(e.values())[0]
                   for e in sub_nav)

    def test_no_repos_produces_only_home(self, tmp_path):
        nav = build_nav.build_nav({}, ["service-", "utility-"])
        assert nav == [{"Home": "index.md"}]

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
# /docs existence check (mocked)
# ---------------------------------------------------------------------------

class TestHasDocsDir:
    def test_returns_true_when_api_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("build_nav.requests.get", return_value=mock_resp):
            assert build_nav.has_docs_dir("service-foo") is True

    def test_returns_false_when_api_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("build_nav.requests.get", return_value=mock_resp):
            assert build_nav.has_docs_dir("service-no-docs") is False

    def test_returns_false_when_api_403(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        with patch("build_nav.requests.get", return_value=mock_resp):
            assert build_nav.has_docs_dir("private-repo") is False

    def test_correct_url_called(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("build_nav.requests.get", return_value=mock_resp) as mock_get:
            build_nav.has_docs_dir("service-foo", "my-org")
            called_url = mock_get.call_args[0][0]
            assert "my-org/service-foo/contents/docs" in called_url


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

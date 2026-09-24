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
    # docs_entries: list of filenames in the docs/ dir (None = 404)
    def _mock_get(self, docs_entries, readme_status: int = 404):
        """Return a side_effect function that returns different responses per URL."""
        def side_effect(url, **kwargs):
            resp = MagicMock()
            if "/contents/docs" in url:
                if docs_entries is None:
                    resp.status_code = 404
                else:
                    resp.status_code = 200
                    resp.json.return_value = [{"name": n} for n in docs_entries]
            else:
                resp.status_code = readme_status
            return resp
        return side_effect

    def test_returns_docs_when_docs_has_readme(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(["README.md", "guide.md"])):
            assert build_nav.get_repo_docs_source("service-foo") == "docs"

    def test_returns_docs_when_docs_has_index(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(["index.md", "extra.md"])):
            assert build_nav.get_repo_docs_source("service-foo") == "docs"

    def test_returns_readme_when_docs_has_no_index(self):
        # docs/ exists but only has supplementary files — fall back to root README
        with patch("build_nav.requests.get", side_effect=self._mock_get(
            ["MCP_VALUE_PROPOSITION.md", "blog.md"], readme_status=200
        )):
            assert build_nav.get_repo_docs_source("service-foo") == "readme"

    def test_returns_none_when_docs_no_index_and_no_readme(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(
            ["supplementary.md"], readme_status=404
        )):
            assert build_nav.get_repo_docs_source("service-foo") is None

    def test_returns_readme_when_no_docs_dir(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(None, readme_status=200)):
            assert build_nav.get_repo_docs_source("service-foo") == "readme"

    def test_returns_none_when_neither_exists(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(None, readme_status=404)):
            assert build_nav.get_repo_docs_source("service-foo") is None

    def test_docs_takes_priority_over_readme(self):
        # docs/ with readme.md wins even if root README also exists
        with patch("build_nav.requests.get", side_effect=self._mock_get(
            ["readme.md"], readme_status=200
        )):
            assert build_nav.get_repo_docs_source("service-foo") == "docs"

    def test_correct_docs_url_called(self):
        with patch("build_nav.requests.get", side_effect=self._mock_get(["index.md"])) as mock_get:
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
# Linked image file parser
# ---------------------------------------------------------------------------

class TestLinkedImageFiles:
    def test_finds_markdown_image(self):
        text = "![diagram](imgs/arch.png)"
        assert "imgs/arch.png" in build_nav._linked_image_files(text)

    def test_finds_html_img_double_quotes(self):
        text = '<img width="100" src="imgs/oh_deploy.png">'
        assert "imgs/oh_deploy.png" in build_nav._linked_image_files(text)

    def test_finds_html_img_single_quotes(self):
        text = "<img src='logo.svg' alt='logo'>"
        assert "logo.svg" in build_nav._linked_image_files(text)

    def test_ignores_http_images(self):
        text = "![remote](https://example.com/image.png)"
        assert build_nav._linked_image_files(text) == []

    def test_ignores_absolute_path_images(self):
        text = "![abs](/static/image.jpg)"
        assert build_nav._linked_image_files(text) == []

    def test_ignores_non_image_extensions(self):
        text = "![file](document.pdf)"
        assert build_nav._linked_image_files(text) == []

    def test_strips_query_and_anchor(self):
        text = "![img](imgs/photo.jpg?v=2#section)"
        assert "imgs/photo.jpg" in build_nav._linked_image_files(text)

    def test_empty_text(self):
        assert build_nav._linked_image_files("") == []

    def test_multiple_images(self):
        text = (
            '<img src="imgs/a.png">\n'
            "![b](imgs/b.gif)\n"
            "![external](https://cdn.example.com/c.png)\n"
        )
        result = build_nav._linked_image_files(text)
        assert "imgs/a.png" in result
        assert "imgs/b.gif" in result
        assert len([r for r in result if "cdn.example.com" in r]) == 0


# ---------------------------------------------------------------------------
# Section index generation
# ---------------------------------------------------------------------------

class TestWriteSectionIndex:
    def test_body_links_use_relative_path_from_sections_dir(self, tmp_path):
        # Patch SECTIONS_DIR to write into tmp_path
        import build_nav as bn
        original = bn.SECTIONS_DIR
        bn.SECTIONS_DIR = str(tmp_path)
        try:
            repos = [("service-foo", "_repos/service-foo/index.md")]
            bn._write_section_index("Services", repos)
            content = (tmp_path / "services" / "index.md").read_text()
            # Body link must be ../../_repos/service-foo/ not the raw docs path
            assert "../../_repos/service-foo/" in content
            assert "_repos/service-foo/index.md" not in content
        finally:
            bn.SECTIONS_DIR = original

    def test_body_links_for_multiple_repos(self, tmp_path):
        import build_nav as bn
        original = bn.SECTIONS_DIR
        bn.SECTIONS_DIR = str(tmp_path)
        try:
            repos = [
                ("service-foo", "_repos/service-foo/index.md"),
                ("service-bar", "_repos/service-bar/index.md"),
            ]
            bn._write_section_index("Services", repos)
            content = (tmp_path / "services" / "index.md").read_text()
            assert "../../_repos/service-foo/" in content
            assert "../../_repos/service-bar/" in content
        finally:
            bn.SECTIONS_DIR = original


# ---------------------------------------------------------------------------
# Front matter injection
# ---------------------------------------------------------------------------

class TestInjectRepoFrontMatter:
    def test_injects_front_matter(self, tmp_path):
        (tmp_path / "index.md").write_text("# Hello\n")
        build_nav._inject_repo_front_matter(
            tmp_path, "service-foo", "https://github.com/open-horizon-services/service-foo"
        )
        content = (tmp_path / "index.md").read_text()
        assert content.startswith("---\n")
        assert "repo_url: https://github.com/open-horizon-services/service-foo\n" in content
        assert "repo_name: open-horizon-services/service-foo\n" in content
        assert "# Hello\n" in content

    def test_does_not_overwrite_existing_front_matter(self, tmp_path):
        original = "---\nrepo_url: https://custom.example.com\n---\n\n# Hello\n"
        (tmp_path / "index.md").write_text(original)
        build_nav._inject_repo_front_matter(
            tmp_path, "service-foo", "https://github.com/open-horizon-services/service-foo"
        )
        assert (tmp_path / "index.md").read_text() == original

    def test_no_op_when_no_index_md(self, tmp_path):
        # Should not raise and should not create any file
        build_nav._inject_repo_front_matter(
            tmp_path, "service-foo", "https://github.com/open-horizon-services/service-foo"
        )
        assert not (tmp_path / "index.md").exists()

    def test_original_content_preserved_after_injection(self, tmp_path):
        body = "# My Repo\n\nSome content here.\n"
        (tmp_path / "index.md").write_text(body)
        build_nav._inject_repo_front_matter(
            tmp_path, "service-bar", "https://github.com/open-horizon-services/service-bar"
        )
        content = (tmp_path / "index.md").read_text()
        assert body in content


# ---------------------------------------------------------------------------
# Readme renaming
# ---------------------------------------------------------------------------

class TestRenameReadmes:
    def test_renames_readme_to_index(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# hello")
        build_nav._rename_readmes(tmp_path)
        assert (tmp_path / "index.md").exists()
        assert not readme.exists()

    def test_renames_lowercase_readme(self, tmp_path):
        readme = tmp_path / "readme.md"
        readme.write_text("# hello")
        build_nav._rename_readmes(tmp_path)
        assert (tmp_path / "index.md").exists()
        assert not readme.exists()

    def test_renames_nested_readme(self, tmp_path):
        sub = tmp_path / "10-excel"
        sub.mkdir()
        (sub / "readme.md").write_text("# sub")
        build_nav._rename_readmes(tmp_path)
        assert (sub / "index.md").exists()
        assert not (sub / "readme.md").exists()

    def test_does_not_overwrite_existing_index(self, tmp_path):
        (tmp_path / "index.md").write_text("# existing index")
        readme = tmp_path / "README.md"
        readme.write_text("# readme")
        build_nav._rename_readmes(tmp_path)
        # index.md must keep original content; README.md must still exist
        assert (tmp_path / "index.md").read_text() == "# existing index"
        assert readme.exists()

    def test_leaves_non_readme_md_untouched(self, tmp_path):
        guide = tmp_path / "guide.md"
        guide.write_text("# guide")
        build_nav._rename_readmes(tmp_path)
        assert guide.exists()
        assert not (tmp_path / "index.md").exists()

    def test_empty_directory(self, tmp_path):
        build_nav._rename_readmes(tmp_path)  # should not raise


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
        nav = build_nav.build_nav(staged, ["service-"])
        # Find the Services section entries
        services = next(item["Services"] for item in nav if "Services" in item)
        foo_entry = next(item for item in services if "service-foo" in item)
        assert foo_entry["service-foo"] == "_repos/service-foo/index.md"

    def test_repo_entry_prefers_readme_or_index_without_subpages(self, tmp_path):
        staged = {
            "service-foo": self._make_staged(tmp_path, "service-foo", ["guide.md", "README.md", "extra.md"]),
        }
        nav = build_nav.build_nav(staged, ["service-"])
        services = next(item["Services"] for item in nav if "Services" in item)
        # Should only contain Overview and repo link, no nested sub-pages list
        foo_entry = next(item for item in services if "service-foo" in item)
        assert foo_entry == {"service-foo": "_repos/service-foo/README.md"}
        assert len(services) == 2  # Overview + service-foo

    def test_repo_entry_prefers_toplevel_readme(self, tmp_path):
        staged = {
            "service-foo": self._make_staged(tmp_path, "service-foo", ["subdir/readme.md", "readme.md"]),
        }
        nav = build_nav.build_nav(staged, ["service-"])
        services = next(item["Services"] for item in nav if "Services" in item)
        foo_entry = next(item for item in services if "service-foo" in item)
        assert foo_entry == {"service-foo": "_repos/service-foo/readme.md"}

    def test_no_repos_produces_only_home(self, tmp_path):
        nav = build_nav.build_nav({}, ["service-", "utility-"])
        assert nav == [{"Home": "index.md"}]

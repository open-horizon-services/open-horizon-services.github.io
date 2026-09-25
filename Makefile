.PHONY: stage serve clean test help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

stage: ## Fetch org repo docs into _docs/ and write mkdocs_build.yml
	python scripts/build_nav.py

serve: stage ## Stage docs then start the MkDocs preview server at http://127.0.0.1:8000
	mkdocs serve -f mkdocs_build.yml

dry-run: ## Show which repositories would be included without cloning anything
	python scripts/build_nav.py --dry-run

test: ## Run unit tests
	python -m pytest tests/ -v

clean: ## Remove staged docs, build output, and generated config
	rm -rf docs/_repos/ docs/_sections/ site/ mkdocs_build.yml __pycache__ .pytest_cache

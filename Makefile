.PHONY: help install install-dev test lint format clean build

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-global: ## Install globally with pipx (use from anywhere!)
	@if ! command -v pipx &> /dev/null; then \
		echo "❌ pipx is not installed"; \
		echo ""; \
		echo "Install it with:"; \
		echo "  brew install pipx"; \
		echo "  pipx ensurepath"; \
		exit 1; \
	fi
	pipx install -e .
	@echo ""
	@echo "✅ Spatelier installed globally!"
	@echo "   You can now use 'spatelier' from anywhere."

install: ## Install the package (requires venv activation)
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Error: Not in a virtual environment!"; \
		echo "   Run: source venv/bin/activate"; \
		echo "   Then run: make install"; \
		exit 1; \
	fi
	pip install -e .

install-dev: ## Install development dependencies (requires venv activation)
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Error: Not in a virtual environment!"; \
		echo "   Run: source venv/bin/activate"; \
		echo "   Then run: make install-dev"; \
		exit 1; \
	fi
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=spatelier --cov-report=html --cov-report=term

lint: ## Run linting
	flake8 spatelier/
	mypy spatelier/

format: ## Format code
	black spatelier/
	isort spatelier/

format-check: ## Check code formatting
	black --check spatelier/
	isort --check-only spatelier/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build package (wheel + source) (requires venv activation)
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Error: Not in a virtual environment!"; \
		echo "   Run: source venv/bin/activate"; \
		echo "   Then run: make build"; \
		exit 1; \
	fi
	python -m build

build-release: ## Build release packages (requires venv activation)
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Error: Not in a virtual environment!"; \
		echo "   Run: source venv/bin/activate"; \
		echo "   Then run: make build-release"; \
		exit 1; \
	fi
	bash scripts/build_release.sh

build-executable: ## Build standalone executable (requires pyinstaller and venv activation)
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Error: Not in a virtual environment!"; \
		echo "   Run: source venv/bin/activate"; \
		echo "   Then run: make build-executable"; \
		exit 1; \
	fi
	bash scripts/build_executable.sh

check: format-check lint test ## Run all checks

sync-version: ## Sync __version__ in spatelier/__init__.py and __init__.py from pyproject.toml (run after bumping version)
	@bash scripts/sync_version.sh

release: ## Create a new release (version in pyproject.toml; run make sync-version first if you bumped it)
	@bash scripts/release.sh

update-homebrew: ## Update Homebrew formula with latest release SHA256 (usage: make update-homebrew TAG=v0.1.0)
	@if [ -z "$(TAG)" ]; then \
		echo "❌ Error: TAG required"; \
		echo "Usage: make update-homebrew TAG=v0.1.0"; \
		exit 1; \
	fi
	@bash scripts/update_homebrew.sh $(TAG)

dev-setup: install-dev ## Set up development environment
	@echo "Development environment set up successfully!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make lint' to run linting"
	@echo "Run 'make format' to format code"

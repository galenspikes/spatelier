"""
Tests for release script and pre-release config hygiene.

Ensures we don't regress on release-script log path and pytest config,
so 'make release' and test runs stay clean.
Also validates that all top-level Python packages are included in the
setuptools manifest so the installed package works (no ModuleNotFoundError).
"""

import re
import subprocess
from pathlib import Path

import pytest

# Project root (parent of tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestReleaseScriptLogPath:
    """Release script must use absolute LOG_FILE so tap subshell can write to it."""

    def test_release_script_sets_repo_root(self):
        """Script must set REPO_ROOT so LOG_FILE can be absolute."""
        release_sh = (PROJECT_ROOT / "scripts" / "release.sh").read_text()
        assert "REPO_ROOT=" in release_sh, "release.sh should set REPO_ROOT"
        assert "git rev-parse --show-toplevel" in release_sh

    def test_release_script_log_dir_uses_repo_root(self):
        """LOG_DIR must be derived from REPO_ROOT (absolute path)."""
        release_sh = (PROJECT_ROOT / "scripts" / "release.sh").read_text()
        assert "LOG_DIR=\"${REPO_ROOT}" in release_sh or 'LOG_DIR="${REPO_ROOT}' in release_sh, (
            "LOG_DIR should use REPO_ROOT so path is absolute when script cd's to tap repo"
        )

    def test_release_script_log_file_uses_log_dir(self):
        """LOG_FILE must use LOG_DIR (not a relative .data/logs)."""
        release_sh = (PROJECT_ROOT / "scripts" / "release.sh").read_text()
        assert "LOG_FILE=\"${LOG_DIR}" in release_sh or 'LOG_FILE="${LOG_DIR}' in release_sh, (
            "LOG_FILE should use LOG_DIR (absolute)"
        )


class TestPytestConfig:
    """Pytest config should be single-source to avoid 'ignoring pytest config in pyproject.toml'."""

    def test_pytest_does_not_warn_about_ignored_pyproject_config(self):
        """Running pytest should not emit 'ignoring pytest config in pyproject.toml'."""
        result = subprocess.run(
            ["pytest", "--co", "-q", "tests/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        stderr = result.stderr or ""
        assert "ignoring pytest config in pyproject.toml" not in stderr, (
            "pytest.ini should be the single source of pytest config; "
            "remove duplicate [tool.pytest.ini_options] from pyproject.toml if this fails"
        )


class TestPytestAlembicWarningFilter:
    """pytest.ini should filter the harmless Alembic MySQL autoincrement warning."""

    def test_pytest_ini_filters_alembic_autoincrement_warning(self):
        """pytest.ini should contain a filter for Alembic autoincrement UserWarning."""
        pytest_ini = (PROJECT_ROOT / "pytest.ini").read_text()
        # We document/filter the Alembic warning; filter line may reference alembic or autoincrement
        assert "alembic" in pytest_ini.lower() or "autoincrement" in pytest_ini.lower(), (
            "pytest.ini should filter Alembic 'autoincrement only make sense for MySQL' warning"
        )
        assert "UserWarning" in pytest_ini or "filterwarnings" in pytest_ini


class TestSetuptoolsPackageManifest:
    """All top-level Python packages must be in setuptools.packages.find.include.

    Prevents ModuleNotFoundError when running the installed package (e.g. via
    Homebrew) because a package was omitted from the manifest.
    """

    # Directories at repo root we do not install as packages
    _EXCLUDE = {"tests", "migrations", "config", "docs", "scripts", "Formula", ".github"}

    def test_all_top_level_packages_in_setuptools_include(self):
        """Every top-level package dir (with __init__.py) must be in pyproject include list."""
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
        match = re.search(r'\[tool\.setuptools\.packages\.find\].*?include\s*=\s*\[(.*?)\]', pyproject, re.DOTALL)
        assert match, "pyproject.toml should have [tool.setuptools.packages.find] include = [...]"
        include_raw = match.group(1)
        include_entries = [s.strip().strip('"').strip("'") for s in re.split(r",\s*", include_raw) if s.strip()]

        top_level_packages = [
            d.name
            for d in PROJECT_ROOT.iterdir()
            if d.is_dir() and (d / "__init__.py").exists() and d.name not in self._EXCLUDE
        ]

        missing = []
        for pkg in top_level_packages:
            covered = any(
                entry == pkg or entry == f"{pkg}*" or (entry.endswith("*") and entry.rstrip("*") == pkg)
                for entry in include_entries
            )
            if not covered:
                missing.append(pkg)

        assert not missing, (
            f"pyproject.toml setuptools.packages.find.include is missing top-level packages: {missing}. "
            "Add e.g. 'domain*' and 'infrastructure*' so the installed package can import them."
        )

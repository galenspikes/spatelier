"""
Tests for release script and pre-release config hygiene.

Ensures we don't regress on release-script log path and pytest config,
so 'make release' and test runs stay clean.
Also validates that all top-level Python packages are included in the
setuptools manifest so the installed package works (no ModuleNotFoundError).
Long-term: test against the built wheel in a clean venv so we catch manifest
drift even if someone edits pyproject without running the manifest test.
"""

import os
import re
import subprocess
import sys
import tempfile
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
    """Single installable package: setuptools must include spatelier* only.

    All code lives under spatelier/; no per-package manifest to maintain.
    """

    def test_single_package_in_setuptools_include(self):
        """pyproject must ship only spatelier (include = ['spatelier*'])."""
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
        match = re.search(r'\[tool\.setuptools\.packages\.find\].*?include\s*=\s*\[(.*?)\]', pyproject, re.DOTALL)
        assert match, "pyproject.toml should have [tool.setuptools.packages.find] include = [...]"
        include_raw = match.group(1)
        include_entries = [s.strip().strip('"').strip("'") for s in re.split(r",\s*", include_raw) if s.strip()]

        assert "spatelier*" in include_entries or "spatelier" in include_entries, (
            "pyproject.toml setuptools.packages.find.include must include 'spatelier*' (single-package layout)."
        )
        spatelier_dir = PROJECT_ROOT / "spatelier"
        assert spatelier_dir.is_dir() and (spatelier_dir / "__init__.py").exists(), (
            "spatelier/ package directory with __init__.py must exist."
        )


class TestInstalledPackageSmoke:
    """Run against the built wheel in a clean venv (no repo on path).

    Long-term guard: if someone removes a package from setuptools include,
    the wheel won't contain it and this test fails. The manifest test above
    only checks pyproject text; this test checks the actual built artifact.
    """

    def test_installed_package_has_domain_and_infrastructure(self):
        """Build wheel, install in clean venv, verify domain and infrastructure import."""
        with tempfile.TemporaryDirectory(prefix="spatelier_install_test_") as tmp:
            tmp_path = Path(tmp)
            wheel_dir = tmp_path / "wheel"
            wheel_dir.mkdir()
            venv_dir = tmp_path / "venv"

            # Build wheel from current source (no network for build)
            build = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "-w",
                    str(wheel_dir),
                    str(PROJECT_ROOT),
                ],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=120,
            )
            assert build.returncode == 0, (
                f"pip wheel failed: {build.stderr or build.stdout}"
            )

            wheels = list(wheel_dir.glob("spatelier-*.whl"))
            assert len(wheels) == 1, f"Expected one wheel, got {wheels}"
            wheel_file = wheels[0]

            # Create clean venv (no repo on path)
            venv_create = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if venv_create.returncode != 0:
                pytest.skip(
                    "Could not create venv for installed-package smoke test: "
                    f"{venv_create.stderr or venv_create.stdout}"
                )

            pip = venv_dir / "bin" / "pip"
            python = venv_dir / "bin" / "python"

            # Install wheel only (no deps) so we only check package layout
            install = subprocess.run(
                [str(pip), "install", "--no-deps", str(wheel_file), "-q"],
                capture_output=True,
                text=True,
                cwd=str(tmp_path),
                timeout=60,
            )
            assert install.returncode == 0, (
                f"pip install wheel failed: {install.stderr or install.stdout}"
            )

            # Run from venv: import spatelier and subpackages (no repo on path)
            run = subprocess.run(
                [str(python), "-c", "import spatelier; import spatelier.domain; import spatelier.infrastructure; print('ok')"],
                capture_output=True,
                text=True,
                cwd=str(tmp_path),
                timeout=10,
                env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
            )
            assert run.returncode == 0, (
                "Installed package missing spatelier.domain or spatelier.infrastructure (ModuleNotFoundError). "
                "Ensure spatelier/ contains all subpackages. "
                f"stderr: {run.stderr} stdout: {run.stdout}"
            )
            assert "ok" in (run.stdout or "")

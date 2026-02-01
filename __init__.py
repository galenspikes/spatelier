"""
Spatelier - Personal tool library for video and music file handling.

When running from repo root without installing (e.g. python __init__.py or
python -c "import sys; sys.path.insert(0, '.'); from spatelier import main; main()"),
this adds the repo to path and delegates to spatelier.cli.app.
Prefer: pip install -e . then use the 'spatelier' console script.
"""

from pathlib import Path
import sys

__version__ = "0.4.1"
__author__ = "Galen Spikes"
__email__ = "galenspikes@gmail.com"


def main():
    """Entry point when run from repo root without installing."""
    sys.path.insert(0, str(Path(__file__).parent))
    from spatelier.cli.app import app
    app()

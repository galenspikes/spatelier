"""
Spatelier - Personal tool library for video and music file handling.
"""

__version__ = "0.1.0"
__author__ = "Galen Spikes"
__email__ = "galenspikes@gmail.com"


def main():
    """Main entry point for spatelier CLI."""
    import sys
    from pathlib import Path

    # Add the current directory to Python path
    sys.path.insert(0, str(Path(__file__).parent))

    from cli.app import app

    app()

"""
Spatelier package shim.

Provides a stable import namespace while the codebase remains in a flat layout.
"""

from __future__ import annotations

import importlib
import sys
from typing import Iterable

__version__ = "0.3.2"
__author__ = "Galen Spikes"
__email__ = "galenspikes@gmail.com"


def _alias_modules(module_names: Iterable[str]) -> None:
    for name in module_names:
        module = importlib.import_module(name)
        sys.modules[f"{__name__}.{name}"] = module


_alias_modules(
    [
        "cli",
        "core",
        "database",
        "modules",
        "analytics",
        "utils",
    ]
)

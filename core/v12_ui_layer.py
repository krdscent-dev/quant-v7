"""Compatibility wrapper for the V12 UI layer.

This module now delegates to :mod:`ui.v12_ui_layer` so the UI layer only
consumes dashboard adapter output.
"""

from __future__ import annotations

from ui.v12_ui_layer import V12UILayer, build_v12_ui

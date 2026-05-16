"""Locations of static assets and Jinja templates."""

from __future__ import annotations

from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

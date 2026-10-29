"""Schemantic: from a description of a system to a finished architecture plate.

Pipeline: YAML spec -> schema and semantic checks -> HTML (CSS Grid, tokens) -> Chromium layout -> connectors
routed against the measured boxes -> layout lint -> native SVG -> PNG rasterised from that SVG. The spec never
holds a coordinate; every position comes from the browser's layout.

This module imports nothing beyond the standard library, so `scripts/doctor.py` can load the package on a
Python that does not have the dependencies yet.
"""

__version__ = "0.3.0.dev0"

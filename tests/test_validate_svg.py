"""Tests for validate_svg.py"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_svg import (
    validate,
    parse_svg,
    check_box_overlaps,
    check_text_overflow,
    check_text_overlaps,
    check_arrow_through_box,
    check_arrow_through_text,
    check_arrow_endpoints,
    check_missing_markers,
    check_spacing,
    check_viewbox,
    check_grid_alignment,
    check_short_arrows,
    check_layer_structure,
    _get_content_boxes,
    _is_group_box,
)


def _write_svg(content: str) -> str:
    """Write SVG content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False)
    f.write(content)
    f.close()
    return f.name


def _validate(svg: str):
    """Shortcut: write SVG, validate, clean up, return issues."""
    path = _write_svg(svg)
    try:
        issues, data = validate(path)
        return issues, data
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Layered structure
# ---------------------------------------------------------------------------

LAYERED_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
  </defs>
  <g id="background"><rect x="0" y="0" width="400" height="300" fill="#FFF"/></g>
  <g id="containers"></g>
  <g id="nodes">
    <rect x="100" y="50" width="200" height="50" rx="8" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
    <rect x="100" y="150" width="200" height="50" rx="8" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  </g>
  <g id="labels">
    <text x="200" y="80" text-anchor="middle" font-family="Arial" font-size="14" fill="#FFF">Box A</text>
    <text x="200" y="180" text-anchor="middle" font-family="Arial" font-size="14" fill="#FFF">Box B</text>
  </g>
  <g id="connections">
    <line x1="200" y1="100" x2="200" y2="150" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
  </g>
</svg>"""


class TestLayerStructure:
    def test_valid_layers_pass(self):
        issues, _ = _validate(LAYERED_TEMPLATE)
        layer_issues = [i for i in issues if "layer" in i.category]
        assert len(layer_issues) == 0

    def test_arrow_in_nodes_fails(self):
        svg = LAYERED_TEMPLATE.replace(
            '<g id="nodes">',
            '<g id="nodes">\n    <line x1="200" y1="100" x2="200" y2="150" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>'
        )
        issues, _ = _validate(svg)
        violations = [i for i in issues if i.category == "layer-violation"]
        assert any("Arrow" in i.message and "#nodes" in i.message for i in violations)

    def test_rect_in_connections_fails(self):
        svg = LAYERED_TEMPLATE.replace(
            '<g id="connections">',
            '<g id="connections">\n    <rect x="50" y="250" width="100" height="30" fill="red"/>'
        )
        issues, _ = _validate(svg)
        violations = [i for i in issues if i.category == "layer-violation"]
        assert any("<rect>" in i.message and "#connections" in i.message for i in violations)

    def test_wrong_layer_order_fails(self):
        svg = LAYERED_TEMPLATE.replace(
            '<g id="nodes">', '<g id="TEMP_NODES">'
        ).replace(
            '<g id="connections">', '<g id="nodes">'
        ).replace(
            '<g id="TEMP_NODES">', '<g id="connections">'
        )
        issues, _ = _validate(svg)
        order_issues = [i for i in issues if i.category == "layer-order"]
        assert len(order_issues) > 0

    def test_no_layers_warns(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <rect x="10" y="10" width="100" height="50" fill="blue"/>
  <text x="60" y="40" text-anchor="middle" font-family="Arial" font-size="14" fill="#FFF">Hi</text>
</svg>"""
        issues, _ = _validate(svg)
        struct_issues = [i for i in issues if i.category == "layer-structure"]
        assert len(struct_issues) > 0
        assert struct_issues[0].severity == "warning"


# ---------------------------------------------------------------------------
# Box overlaps
# ---------------------------------------------------------------------------

class TestBoxOverlaps:
    def test_overlapping_boxes(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200">
  <rect x="50" y="50" width="150" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="100" y="70" width="150" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        overlaps = [i for i in issues if i.category == "box-overlap"]
        assert len(overlaps) == 1

    def test_non_overlapping_passes(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200">
  <rect x="50" y="50" width="100" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="200" y="50" width="100" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        overlaps = [i for i in issues if i.category == "box-overlap"]
        assert len(overlaps) == 0

    def test_group_background_ignored(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <rect x="30" y="30" width="340" height="240" rx="10" fill="#F0F4F8" stroke-dasharray="6,3"/>
  <rect x="100" y="60" width="200" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="100" y="150" width="200" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        overlaps = [i for i in issues if i.category == "box-overlap"]
        assert len(overlaps) == 0


# ---------------------------------------------------------------------------
# Text overflow
# ---------------------------------------------------------------------------

class TestTextOverflow:
    def test_text_overflows_box(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="300" height="200">
  <rect x="50" y="50" width="60" height="40" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  <text x="80" y="73" text-anchor="middle" font-family="Arial" font-size="16" fill="#FFF">Very Long Label Here</text>
</svg>"""
        issues, _ = _validate(svg)
        overflows = [i for i in issues if i.category == "text-overflow"]
        assert len(overflows) > 0

    def test_text_fits_passes(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="300" height="200">
  <rect x="50" y="50" width="200" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  <text x="150" y="80" text-anchor="middle" font-family="Arial" font-size="14" fill="#FFF">Short</text>
</svg>"""
        issues, _ = _validate(svg)
        overflows = [i for i in issues if i.category == "text-overflow"]
        assert len(overflows) == 0


# ---------------------------------------------------------------------------
# Text overlaps
# ---------------------------------------------------------------------------

class TestTextOverlaps:
    def test_overlapping_text(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="300" height="200">
  <text x="100" y="80" font-family="Arial" font-size="16" fill="#000">Hello World</text>
  <text x="105" y="82" font-family="Arial" font-size="16" fill="#000">Overlap Me</text>
</svg>"""
        issues, _ = _validate(svg)
        overlaps = [i for i in issues if i.category == "text-overlap"]
        assert len(overlaps) > 0


# ---------------------------------------------------------------------------
# Arrow through box
# ---------------------------------------------------------------------------

class TestArrowThroughBox:
    def test_arrow_crosses_box(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <rect x="50" y="50" width="100" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="50" y="150" width="100" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="170" y="100" width="80" height="40" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  <line x1="100" y1="100" x2="100" y2="150" stroke="#4A5568" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        # The vertical line at x=100 shouldn't cross the box at x=170, so no arrow-through-box
        # This tests that adjacent boxes don't false-positive
        through = [i for i in issues if i.category == "arrow-through-box"]
        assert len(through) == 0


# ---------------------------------------------------------------------------
# Arrow through text
# ---------------------------------------------------------------------------

class TestArrowThroughText:
    def test_arrow_crosses_label(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
  </defs>
  <text x="200" y="150" text-anchor="middle" font-family="Arial" font-size="16" fill="#000">Center Label</text>
  <line x1="200" y1="50" x2="200" y2="250" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
</svg>"""
        issues, _ = _validate(svg)
        through = [i for i in issues if i.category == "arrow-through-text"]
        assert len(through) > 0

    def test_arrow_avoids_label(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <text x="100" y="80" text-anchor="middle" font-family="Arial" font-size="14" fill="#000">Left Label</text>
  <line x1="300" y1="50" x2="300" y2="250" stroke="#4A5568" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        through = [i for i in issues if i.category == "arrow-through-text"]
        assert len(through) == 0


# ---------------------------------------------------------------------------
# Missing markers
# ---------------------------------------------------------------------------

class TestMissingMarkers:
    def test_undefined_marker(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="300" height="200">
  <defs></defs>
  <line x1="50" y1="50" x2="200" y2="50" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
</svg>"""
        issues, _ = _validate(svg)
        missing = [i for i in issues if i.category == "missing-marker"]
        assert len(missing) == 1

    def test_defined_marker_passes(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="300" height="200">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
  </defs>
  <line x1="50" y1="50" x2="200" y2="50" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
</svg>"""
        issues, _ = _validate(svg)
        missing = [i for i in issues if i.category == "missing-marker"]
        assert len(missing) == 0


# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------

class TestSpacing:
    def test_tight_boxes_warned(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200">
  <rect x="50" y="50" width="100" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="50" y="110" width="100" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        tight = [i for i in issues if i.category == "tight-spacing"]
        assert len(tight) > 0


# ---------------------------------------------------------------------------
# ViewBox
# ---------------------------------------------------------------------------

class TestViewBox:
    def test_content_exceeds_viewbox(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" width="200" height="100">
  <rect x="50" y="50" width="200" height="80" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        vb = [i for i in issues if i.category == "viewbox" and i.severity == "error"]
        assert len(vb) > 0

    def test_no_viewbox_errors(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect x="10" y="10" width="50" height="50" fill="blue"/></svg>'
        issues, _ = _validate(svg)
        vb = [i for i in issues if i.category == "viewbox"]
        assert any("No viewBox" in i.message for i in vb)


# ---------------------------------------------------------------------------
# Grid alignment
# ---------------------------------------------------------------------------

class TestGridAlignment:
    def test_misaligned_boxes_warned(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <rect x="100" y="50" width="100" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="105" y="140" width="100" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  <rect x="100" y="230" width="100" height="50" fill="#E8854A" stroke="#C46A2F" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        grid = [i for i in issues if i.category == "grid-alignment"]
        assert len(grid) > 0


# ---------------------------------------------------------------------------
# Short arrows
# ---------------------------------------------------------------------------

class TestShortArrows:
    def test_tiny_arrow_warned(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <line x1="100" y1="100" x2="105" y2="103" stroke="#4A5568" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        short = [i for i in issues if i.category == "short-arrow"]
        assert len(short) > 0


# ---------------------------------------------------------------------------
# Group detection
# ---------------------------------------------------------------------------

class TestGroupDetection:
    def test_dashed_stroke_is_group(self):
        path = _write_svg("""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <rect x="30" y="30" width="340" height="240" rx="10" fill="#F0F4F8" stroke="#4A5568" stroke-dasharray="6,3"/>
  <rect x="100" y="60" width="200" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="100" y="160" width="200" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>""")
        try:
            data = parse_svg(path)
            content = _get_content_boxes(data["boxes"])
            assert len(content) == 2  # only the inner boxes
            group_box = [b for b in data["boxes"] if b not in content]
            assert len(group_box) == 1
        finally:
            os.unlink(path)

    def test_light_fill_large_rect_is_group(self):
        path = _write_svg("""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <rect x="20" y="20" width="360" height="260" rx="10" fill="#F0F4F8"/>
  <rect x="100" y="60" width="200" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="100" y="160" width="200" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>""")
        try:
            data = parse_svg(path)
            content = _get_content_boxes(data["boxes"])
            assert len(content) == 2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Example SVG passes all checks
# ---------------------------------------------------------------------------

class TestExampleSVG:
    def test_tc3_boot_flow_passes(self):
        example = os.path.join(os.path.dirname(__file__), "..", "examples", "tc3_boot_flow.svg")
        if not os.path.isfile(example):
            pytest.skip("Example SVG not found")
        issues, data = validate(example)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Example SVG has errors: {[e.message for e in errors]}"

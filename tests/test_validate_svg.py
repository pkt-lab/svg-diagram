"""Tests for validate_svg.py — focused on tricky logic that's easy to break."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_svg import validate, parse_svg, _get_content_boxes


def _validate(svg: str):
    """Write SVG to temp file, validate, clean up, return issues."""
    f = tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False)
    f.write(svg)
    f.close()
    try:
        issues, data = validate(f.name)
        return issues, data
    finally:
        os.unlink(f.name)


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
        assert not [i for i in issues if "layer" in i.category]

    def test_arrow_in_nodes_fails(self):
        svg = LAYERED_TEMPLATE.replace(
            '<g id="nodes">',
            '<g id="nodes">\n    <line x1="200" y1="100" x2="200" y2="150" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>'
        )
        issues, _ = _validate(svg)
        assert any(i.category == "layer-violation" and "#nodes" in i.message for i in issues)

    def test_rect_in_connections_fails(self):
        svg = LAYERED_TEMPLATE.replace(
            '<g id="connections">',
            '<g id="connections">\n    <rect x="50" y="250" width="100" height="30" fill="red"/>'
        )
        issues, _ = _validate(svg)
        assert any(i.category == "layer-violation" and "#connections" in i.message for i in issues)

    def test_wrong_layer_order_fails(self):
        svg = LAYERED_TEMPLATE.replace(
            '<g id="nodes">', '<g id="TEMP">'
        ).replace(
            '<g id="connections">', '<g id="nodes">'
        ).replace(
            '<g id="TEMP">', '<g id="connections">'
        )
        issues, _ = _validate(svg)
        assert any(i.category == "layer-order" for i in issues)

    def test_no_layers_warns(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200"><rect x="10" y="10" width="100" height="50" fill="blue"/></svg>'
        issues, _ = _validate(svg)
        struct = [i for i in issues if i.category == "layer-structure"]
        assert struct and struct[0].severity == "warning"


class TestGroupDetection:
    def test_dashed_stroke_is_group(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <rect x="30" y="30" width="340" height="240" rx="10" fill="#F0F4F8" stroke="#4A5568" stroke-dasharray="6,3"/>
  <rect x="100" y="60" width="200" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="100" y="160" width="200" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>"""
        f = tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False)
        f.write(svg)
        f.close()
        try:
            data = parse_svg(f.name)
            content = _get_content_boxes(data["boxes"])
            assert len(content) == 2
        finally:
            os.unlink(f.name)

    def test_light_fill_large_rect_is_group(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <rect x="20" y="20" width="360" height="260" rx="10" fill="#F0F4F8"/>
  <rect x="100" y="60" width="200" height="50" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <rect x="100" y="160" width="200" height="50" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
</svg>"""
        f = tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False)
        f.write(svg)
        f.close()
        try:
            data = parse_svg(f.name)
            assert len(_get_content_boxes(data["boxes"])) == 2
        finally:
            os.unlink(f.name)


class TestArrowThroughText:
    def test_arrow_crosses_label(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/></marker></defs>
  <text x="200" y="150" text-anchor="middle" font-family="Arial" font-size="16" fill="#000">Center Label</text>
  <line x1="200" y1="50" x2="200" y2="250" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
</svg>"""
        issues, _ = _validate(svg)
        assert any(i.category == "arrow-through-text" for i in issues)

    def test_arrow_avoids_label(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <text x="100" y="80" text-anchor="middle" font-family="Arial" font-size="14" fill="#000">Left Label</text>
  <line x1="300" y1="50" x2="300" y2="250" stroke="#4A5568" stroke-width="2"/>
</svg>"""
        issues, _ = _validate(svg)
        assert not [i for i in issues if i.category == "arrow-through-text"]


class TestExampleSVGs:
    def test_tc3_boot_flow_passes(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "tc3_boot_flow.svg")
        if not os.path.isfile(path):
            pytest.skip("Example SVG not found")
        issues, _ = validate(path)
        errors = [i for i in issues if i.severity == "error"]
        assert not errors, f"Errors: {[e.message for e in errors]}"

    def test_qemu_architecture_passes(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "qemu_virtio_architecture.svg")
        if not os.path.isfile(path):
            pytest.skip("Example SVG not found")
        issues, _ = validate(path)
        errors = [i for i in issues if i.severity == "error"]
        assert not errors, f"Errors: {[e.message for e in errors]}"

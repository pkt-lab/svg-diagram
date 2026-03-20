#!/usr/bin/env python3
"""
SVG Diagram Validator
Checks SVG diagrams for common layout issues: overlapping boxes, text overflow,
arrows passing through boxes, misaligned grids, and missing markers.

Usage:
    python3 scripts/validate_svg.py <file.svg>
    python3 scripts/validate_svg.py <file.svg> --fix > fixed.svg
    python3 scripts/validate_svg.py <directory>   # validates all .svg files

Exit codes:
    0 = all checks passed
    1 = warnings only (diagram is usable but could be improved)
    2 = errors found (diagram has overlap/readability issues)
"""

import sys
import os
import re
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

NS = {"svg": "http://www.w3.org/2000/svg"}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Box:
    """A rectangle element in the SVG."""
    id: str
    x: float
    y: float
    width: float
    height: float
    elem: object = field(repr=False, default=None)

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def cx(self):
        return self.x + self.width / 2

    @property
    def cy(self):
        return self.y + self.height / 2


@dataclass
class TextEl:
    """A text element in the SVG."""
    id: str
    x: float
    y: float
    text: str
    font_size: float
    anchor: str  # start, middle, end
    estimated_width: float
    estimated_height: float
    elem: object = field(repr=False, default=None)

    @property
    def left(self):
        if self.anchor == "middle":
            return self.x - self.estimated_width / 2
        elif self.anchor == "end":
            return self.x - self.estimated_width
        return self.x

    @property
    def right(self):
        return self.left + self.estimated_width

    @property
    def top(self):
        return self.y - self.estimated_height * 0.7  # approx ascent

    @property
    def bottom(self):
        return self.y + self.estimated_height * 0.3  # approx descent


@dataclass
class Line:
    """A line or path connection."""
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    waypoints: list = field(default_factory=list)  # for paths
    has_marker: bool = False


@dataclass
class Issue:
    severity: str  # "error" or "warning"
    category: str
    message: str
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Character width estimation (matches SKILL.md rules)
# ---------------------------------------------------------------------------

CHAR_WIDTH = {
    11: 6.2,
    12: 7.0,
    13: 7.5,
    14: 8.2,
    15: 8.8,
    16: 9.4,
    18: 10.5,
    20: 11.8,
}


def estimate_text_width(text: str, font_size: float, bold: bool = False) -> float:
    base = CHAR_WIDTH.get(int(font_size), font_size * 0.58)
    width = len(text) * base
    if bold:
        width *= 1.1
    return width


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_svg(filepath: str):
    tree = ET.parse(filepath)
    root = tree.getroot()

    boxes: list[Box] = []
    texts: list[TextEl] = []
    lines: list[Line] = []
    markers_defined: set[str] = set()
    markers_used: set[str] = set()
    viewbox = root.get("viewBox", "")
    svg_width = root.get("width", "")
    svg_height = root.get("height", "")

    counter = {"rect": 0, "text": 0, "line": 0, "path": 0}

    for elem in root.iter():
        tag = strip_ns(elem.tag)

        if tag == "marker":
            mid = elem.get("id", "")
            if mid:
                markers_defined.add(mid)

        elif tag == "rect":
            x = _float(elem.get("x", "0"))
            y = _float(elem.get("y", "0"))
            w = _float(elem.get("width", "0"))
            h = _float(elem.get("height", "0"))
            if w > 0 and h > 0:
                counter["rect"] += 1
                boxes.append(Box(
                    id=f"rect#{counter['rect']}",
                    x=x, y=y, width=w, height=h, elem=elem
                ))

        elif tag == "text":
            x = _float(elem.get("x", "0"))
            y = _float(elem.get("y", "0"))
            anchor = elem.get("text-anchor", "start")
            fs = _float(elem.get("font-size", "16"))
            bold = elem.get("font-weight", "") == "bold"
            txt = _get_all_text(elem)
            if txt.strip():
                counter["text"] += 1
                ew = estimate_text_width(txt, fs, bold)
                texts.append(TextEl(
                    id=f"text#{counter['text']}",
                    x=x, y=y, text=txt, font_size=fs,
                    anchor=anchor, estimated_width=ew,
                    estimated_height=fs, elem=elem
                ))

        elif tag == "line":
            x1 = _float(elem.get("x1", "0"))
            y1 = _float(elem.get("y1", "0"))
            x2 = _float(elem.get("x2", "0"))
            y2 = _float(elem.get("y2", "0"))
            counter["line"] += 1
            has_marker = bool(elem.get("marker-end", ""))
            _collect_marker_refs(elem, markers_used)
            lines.append(Line(
                id=f"line#{counter['line']}",
                x1=x1, y1=y1, x2=x2, y2=y2,
                has_marker=has_marker
            ))

        elif tag == "path":
            d = elem.get("d", "")
            fill = elem.get("fill", "")
            # Only treat as connector if fill is none (not a shape fill)
            if d and fill.lower() in ("none", ""):
                pts = _parse_path_endpoints(d)
                if pts and len(pts) >= 2:
                    counter["path"] += 1
                    has_marker = bool(elem.get("marker-end", ""))
                    _collect_marker_refs(elem, markers_used)
                    lines.append(Line(
                        id=f"path#{counter['path']}",
                        x1=pts[0][0], y1=pts[0][1],
                        x2=pts[-1][0], y2=pts[-1][1],
                        waypoints=pts,
                        has_marker=has_marker
                    ))

    return {
        "boxes": boxes,
        "texts": texts,
        "lines": lines,
        "markers_defined": markers_defined,
        "markers_used": markers_used,
        "viewbox": viewbox,
        "svg_width": svg_width,
        "svg_height": svg_height,
        "root": root,
        "tree": tree,
    }


def _float(s: str) -> float:
    try:
        return float(re.sub(r"[^\d.\-]", "", s))
    except (ValueError, TypeError):
        return 0.0


def _get_all_text(elem) -> str:
    parts = []
    if elem.text:
        parts.append(elem.text.strip())
    for child in elem:
        parts.append(_get_all_text(child))
        if child.tail:
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def _collect_marker_refs(elem, marker_set: set):
    for attr in ("marker-end", "marker-start", "marker-mid"):
        val = elem.get(attr, "")
        m = re.search(r"url\(#([^)]+)\)", val)
        if m:
            marker_set.add(m.group(1))


def _parse_path_endpoints(d: str) -> list[tuple[float, float]]:
    """Extract key points from a path d attribute."""
    points = []
    # Match M/L/C/Q commands with coordinates
    tokens = re.findall(r"([MLCQHVZ])\s*([^MLCQHVZ]*)", d, re.IGNORECASE)
    for cmd, args in tokens:
        nums = re.findall(r"-?\d+\.?\d*", args)
        cmd_upper = cmd.upper()
        if cmd_upper == "M" and len(nums) >= 2:
            points.append((float(nums[0]), float(nums[1])))
        elif cmd_upper == "L" and len(nums) >= 2:
            # Take pairs
            for i in range(0, len(nums) - 1, 2):
                points.append((float(nums[i]), float(nums[i + 1])))
        elif cmd_upper == "C" and len(nums) >= 6:
            # Cubic bezier - take endpoint
            points.append((float(nums[4]), float(nums[5])))
        elif cmd_upper == "Q" and len(nums) >= 4:
            points.append((float(nums[2]), float(nums[3])))
        elif cmd_upper == "H" and len(nums) >= 1:
            if points:
                points.append((float(nums[0]), points[-1][1]))
        elif cmd_upper == "V" and len(nums) >= 1:
            if points:
                points.append((points[-1][0], float(nums[0])))
    return points


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

def check_box_overlaps(boxes: list[Box]) -> list[Issue]:
    """Check if any two content boxes overlap (excluding background/group rects)."""
    issues = []
    content_boxes = _get_content_boxes(boxes)

    for i, a in enumerate(content_boxes):
        for b in content_boxes[i + 1:]:
            if _rects_overlap(a, b):
                overlap_x = min(a.right, b.right) - max(a.x, b.x)
                overlap_y = min(a.bottom, b.bottom) - max(a.y, b.y)
                issues.append(Issue(
                    severity="error",
                    category="box-overlap",
                    message=f"{a.id} and {b.id} overlap by {overlap_x:.0f}x{overlap_y:.0f}px",
                    suggestion=f"Move {b.id} so its x >= {a.right + 10:.0f} or y >= {a.bottom + 10:.0f}"
                ))
    return issues


def check_text_overflow(boxes: list[Box], texts: list[TextEl]) -> list[Issue]:
    """Check if text extends beyond its containing box."""
    issues = []
    for t in texts:
        container = _find_container(t, boxes)
        if container is None:
            continue  # standalone text (title, annotation)

        margin = 8  # px tolerance
        if t.left < container.x - margin:
            overflow = container.x - t.left
            issues.append(Issue(
                severity="error",
                category="text-overflow",
                message=f'"{t.text}" overflows LEFT of {container.id} by {overflow:.0f}px',
                suggestion=f"Widen box to {t.estimated_width + 40:.0f}px or shorten text"
            ))
        if t.right > container.right + margin:
            overflow = t.right - container.right
            issues.append(Issue(
                severity="error",
                category="text-overflow",
                message=f'"{t.text}" overflows RIGHT of {container.id} by {overflow:.0f}px',
                suggestion=f"Widen box to {t.estimated_width + 40:.0f}px or shorten text"
            ))
    return issues


def check_text_overlaps(texts: list[TextEl]) -> list[Issue]:
    """Check if any two text elements overlap each other."""
    issues = []
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if _text_rects_overlap(a, b):
                issues.append(Issue(
                    severity="error",
                    category="text-overlap",
                    message=f'"{a.text}" and "{b.text}" overlap',
                    suggestion="Increase spacing between components or reduce font size"
                ))
    return issues


def check_arrow_through_box(lines: list[Line], boxes: list[Box]) -> list[Issue]:
    """Check if any arrow/line passes through a box it doesn't start/end at."""
    issues = []
    content_boxes = _get_content_boxes(boxes)

    for line in lines:
        for box in content_boxes:
            # Skip if line starts or ends at/near this box
            if _point_near_box(line.x1, line.y1, box, tolerance=5):
                continue
            if _point_near_box(line.x2, line.y2, box, tolerance=5):
                continue

            # Check if line segment intersects box
            if line.waypoints:
                for j in range(len(line.waypoints) - 1):
                    p1 = line.waypoints[j]
                    p2 = line.waypoints[j + 1]
                    if _segment_intersects_box(p1[0], p1[1], p2[0], p2[1], box):
                        issues.append(Issue(
                            severity="error",
                            category="arrow-through-box",
                            message=f"{line.id} passes through {box.id}",
                            suggestion="Route arrow around the box using orthogonal path segments"
                        ))
                        break
            else:
                if _segment_intersects_box(line.x1, line.y1, line.x2, line.y2, box):
                    issues.append(Issue(
                        severity="error",
                        category="arrow-through-box",
                        message=f"{line.id} passes through {box.id}",
                        suggestion="Route arrow around the box using orthogonal path segments"
                    ))
    return issues


def check_arrow_through_text(lines: list[Line], texts: list[TextEl]) -> list[Issue]:
    """Check if any arrow passes through a text label's bounding area."""
    issues = []
    for line in lines:
        for t in texts:
            # Build a bounding box for the text with padding
            pad = 4  # px tolerance around text
            t_left = t.left - pad
            t_right = t.right + pad
            t_top = t.top - pad
            t_bottom = t.bottom + pad

            if t_right - t_left <= 0 or t_bottom - t_top <= 0:
                continue

            # Create a temporary Box for intersection testing
            text_box = Box(
                id=t.id, x=t_left, y=t_top,
                width=t_right - t_left, height=t_bottom - t_top
            )

            # Check segments
            if line.waypoints:
                for j in range(len(line.waypoints) - 1):
                    p1 = line.waypoints[j]
                    p2 = line.waypoints[j + 1]
                    if _segment_intersects_box(p1[0], p1[1], p2[0], p2[1], text_box):
                        issues.append(Issue(
                            severity="error",
                            category="arrow-through-text",
                            message=f'{line.id} passes through label "{t.text}"',
                            suggestion="Route arrow to avoid the text area, or reposition the label"
                        ))
                        break
            else:
                if _segment_intersects_box(line.x1, line.y1, line.x2, line.y2, text_box):
                    issues.append(Issue(
                        severity="error",
                        category="arrow-through-text",
                        message=f'{line.id} passes through label "{t.text}"',
                        suggestion="Route arrow to avoid the text area, or reposition the label"
                    ))
    return issues


def check_arrow_endpoints(lines: list[Line], boxes: list[Box]) -> list[Issue]:
    """Check that arrows start/end at box edges, not centers or outside."""
    issues = []
    content_boxes = _get_content_boxes(boxes)

    for line in lines:
        # Check start point
        start_box = _find_nearest_box(line.x1, line.y1, content_boxes, tolerance=15)
        if start_box and not _point_near_edge(line.x1, line.y1, start_box, tolerance=8):
            issues.append(Issue(
                severity="warning",
                category="arrow-endpoint",
                message=f"{line.id} starts inside {start_box.id} (not at edge)",
                suggestion="Arrow should start at box edge: top/bottom/left/right center"
            ))

        # Check end point
        end_box = _find_nearest_box(line.x2, line.y2, content_boxes, tolerance=15)
        if end_box and not _point_near_edge(line.x2, line.y2, end_box, tolerance=8):
            issues.append(Issue(
                severity="warning",
                category="arrow-endpoint",
                message=f"{line.id} ends inside {end_box.id} (not at edge)",
                suggestion="Arrow should end at box edge: top/bottom/left/right center"
            ))
    return issues


def check_missing_markers(markers_defined: set, markers_used: set) -> list[Issue]:
    """Check for marker references that don't have definitions."""
    issues = []
    for m in markers_used:
        if m not in markers_defined:
            issues.append(Issue(
                severity="error",
                category="missing-marker",
                message=f"Marker '{m}' is referenced but not defined in <defs>",
                suggestion=f"Add <marker id=\"{m}\"> to <defs>"
            ))
    return issues


def check_spacing(boxes: list[Box]) -> list[Issue]:
    """Check minimum spacing between adjacent boxes."""
    issues = []
    content_boxes = _get_content_boxes(boxes)
    min_gap = 30  # px - warning threshold

    for i, a in enumerate(content_boxes):
        for b in content_boxes[i + 1:]:
            if _rects_overlap(a, b):
                continue  # already caught by overlap check

            # Calculate edge-to-edge distance
            gap_x = max(0, max(b.x - a.right, a.x - b.right))
            gap_y = max(0, max(b.y - a.bottom, a.y - b.bottom))

            # Only check boxes that are roughly aligned (same row or column)
            if gap_y == 0 and 0 < gap_x < min_gap:
                issues.append(Issue(
                    severity="warning",
                    category="tight-spacing",
                    message=f"{a.id} and {b.id} are only {gap_x:.0f}px apart horizontally",
                    suggestion=f"Increase horizontal gap to at least {min_gap}px"
                ))
            elif gap_x == 0 and 0 < gap_y < min_gap:
                issues.append(Issue(
                    severity="warning",
                    category="tight-spacing",
                    message=f"{a.id} and {b.id} are only {gap_y:.0f}px apart vertically",
                    suggestion=f"Increase vertical gap to at least {min_gap}px"
                ))
    return issues


def check_viewbox(data: dict) -> list[Issue]:
    """Check that viewBox matches content bounds."""
    issues = []
    boxes = data["boxes"]
    texts = data["texts"]
    vb = data["viewbox"]

    if not vb:
        issues.append(Issue(
            severity="error",
            category="viewbox",
            message="No viewBox attribute on <svg>",
            suggestion="Add viewBox=\"0 0 WIDTH HEIGHT\" matching content size"
        ))
        return issues

    parts = vb.split()
    if len(parts) != 4:
        return issues

    vb_w, vb_h = float(parts[2]), float(parts[3])

    # Find content bounds
    max_x = 0
    max_y = 0
    for b in boxes:
        max_x = max(max_x, b.right)
        max_y = max(max_y, b.bottom)
    for t in texts:
        max_x = max(max_x, t.right)
        max_y = max(max_y, t.bottom)

    if max_x > 0 and max_y > 0:
        if max_x > vb_w:
            issues.append(Issue(
                severity="error",
                category="viewbox",
                message=f"Content extends to x={max_x:.0f} but viewBox width is {vb_w:.0f}",
                suggestion=f"Set viewBox width to at least {max_x + 30:.0f}"
            ))
        if max_y > vb_h:
            issues.append(Issue(
                severity="error",
                category="viewbox",
                message=f"Content extends to y={max_y:.0f} but viewBox height is {vb_h:.0f}",
                suggestion=f"Set viewBox height to at least {max_y + 30:.0f}"
            ))
        if vb_w > max_x * 1.8 and vb_w > 200:
            issues.append(Issue(
                severity="warning",
                category="viewbox",
                message=f"viewBox width ({vb_w:.0f}) is much larger than content ({max_x:.0f})",
                suggestion="Shrink viewBox to fit content with ~30px padding"
            ))
        if vb_h > max_y * 1.8 and vb_h > 200:
            issues.append(Issue(
                severity="warning",
                category="viewbox",
                message=f"viewBox height ({vb_h:.0f}) is much larger than content ({max_y:.0f})",
                suggestion="Shrink viewBox to fit content with ~30px padding"
            ))
    return issues


def check_grid_alignment(boxes: list[Box]) -> list[Issue]:
    """Check that boxes align to a consistent grid."""
    issues = []
    content_boxes = _get_content_boxes(boxes)
    if len(content_boxes) < 3:
        return issues  # too few boxes to judge

    # Check x-position clustering
    x_positions = sorted(set(b.x for b in content_boxes))
    y_positions = sorted(set(b.y for b in content_boxes))

    # Find boxes that are close but not aligned
    for i, x1 in enumerate(x_positions):
        for x2 in x_positions[i + 1:]:
            diff = x2 - x1
            if 1 < diff < 15:
                issues.append(Issue(
                    severity="warning",
                    category="grid-alignment",
                    message=f"Boxes at x={x1:.0f} and x={x2:.0f} are {diff:.0f}px apart — likely misaligned",
                    suggestion=f"Align both to x={x1:.0f}"
                ))

    for i, y1 in enumerate(y_positions):
        for y2 in y_positions[i + 1:]:
            diff = y2 - y1
            if 1 < diff < 15:
                issues.append(Issue(
                    severity="warning",
                    category="grid-alignment",
                    message=f"Boxes at y={y1:.0f} and y={y2:.0f} are {diff:.0f}px apart — likely misaligned",
                    suggestion=f"Align both to y={y1:.0f}"
                ))

    return issues


def check_short_arrows(lines: list[Line]) -> list[Issue]:
    """Check for arrows that are too short to be visible."""
    issues = []
    for line in lines:
        length = math.sqrt((line.x2 - line.x1) ** 2 + (line.y2 - line.y1) ** 2)
        if 0 < length < 15:
            issues.append(Issue(
                severity="warning",
                category="short-arrow",
                message=f"{line.id} is only {length:.0f}px long — arrowhead may be invisible",
                suggestion="Increase spacing between connected boxes to at least 30px"
            ))
    return issues


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _rects_overlap(a: Box, b: Box) -> bool:
    return not (a.right <= b.x or b.right <= a.x or a.bottom <= b.y or b.bottom <= a.y)


def _contains(outer: Box, inner: Box) -> bool:
    return (outer.x <= inner.x and outer.y <= inner.y and
            outer.right >= inner.right and outer.bottom >= inner.bottom)


def _text_rects_overlap(a: TextEl, b: TextEl) -> bool:
    return not (a.right <= b.left or b.right <= a.left or a.bottom <= b.top or b.bottom <= a.top)


def _find_container(t: TextEl, boxes: list[Box]) -> Optional[Box]:
    """Find the smallest box that contains this text's anchor point."""
    candidates = []
    for b in boxes:
        if b.x <= t.x <= b.right and b.y <= t.y <= b.bottom:
            candidates.append(b)
    if not candidates:
        return None
    # Return the smallest containing box
    return min(candidates, key=lambda b: b.width * b.height)


def _point_near_box(px: float, py: float, box: Box, tolerance: float) -> bool:
    """Check if a point is at or near a box edge."""
    return (box.x - tolerance <= px <= box.right + tolerance and
            box.y - tolerance <= py <= box.bottom + tolerance)


def _point_near_edge(px: float, py: float, box: Box, tolerance: float) -> bool:
    """Check if a point is near one of the 4 edges of a box (not the interior)."""
    near_left = abs(px - box.x) <= tolerance
    near_right = abs(px - box.right) <= tolerance
    near_top = abs(py - box.y) <= tolerance
    near_bottom = abs(py - box.bottom) <= tolerance

    in_x = box.x - tolerance <= px <= box.right + tolerance
    in_y = box.y - tolerance <= py <= box.bottom + tolerance

    return (near_top and in_x) or (near_bottom and in_x) or (near_left and in_y) or (near_right and in_y)


def _find_nearest_box(px: float, py: float, boxes: list[Box], tolerance: float) -> Optional[Box]:
    """Find the box whose edge is closest to the point, within tolerance."""
    for box in boxes:
        if _point_near_box(px, py, box, tolerance):
            return box
    return None


def _segment_intersects_box(x1, y1, x2, y2, box: Box) -> bool:
    """Check if a line segment intersects a box (excluding endpoints near box)."""
    # Shrink box slightly to avoid false positives at edges
    bx, by = box.x + 3, box.y + 3
    bw, bh = box.width - 6, box.height - 6
    if bw <= 0 or bh <= 0:
        return False

    # Cohen-Sutherland-like clipping check
    edges = [
        (bx, by, bx + bw, by),           # top
        (bx, by + bh, bx + bw, by + bh), # bottom
        (bx, by, bx, by + bh),           # left
        (bx + bw, by, bx + bw, by + bh), # right
    ]
    for ex1, ey1, ex2, ey2 in edges:
        if _segments_intersect(x1, y1, x2, y2, ex1, ey1, ex2, ey2):
            return True
    return False


def _segments_intersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2) -> bool:
    """Check if two line segments intersect."""
    def cross(ox, oy, ax, ay, bx, by):
        return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)

    d1 = cross(bx1, by1, bx2, by2, ax1, ay1)
    d2 = cross(bx1, by1, bx2, by2, ax2, ay2)
    d3 = cross(ax1, ay1, ax2, ay2, bx1, by1)
    d4 = cross(ax1, ay1, ax2, ay2, bx2, by2)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False


def _get_content_boxes(boxes: list[Box]) -> list[Box]:
    """Filter out group/background rectangles, keeping content boxes."""
    content = []
    group = []
    for b in boxes:
        if _is_group_box(b):
            group.append(b)
        else:
            content.append(b)

    # Also catch unmarked group boxes by containment: if a box fully contains 2+ content boxes
    final_content = []
    for b in content:
        contained = sum(1 for cb in content if cb is not b and _contains(b, cb))
        if contained >= 2:
            group.append(b)
        else:
            final_content.append(b)
    return final_content


def _is_group_box(box: Box) -> bool:
    """Detect group/background rectangles by visual attributes."""
    elem = box.elem
    if elem is None:
        return False
    # Dashed stroke → group/background
    if elem.get("stroke-dasharray"):
        return True
    # Very light fills are typically backgrounds
    fill = (elem.get("fill") or "").lower()
    bg_fills = {"#f0f4f8", "#e2e8f0", "#f7fafc", "#edf2f7", "#fff", "#ffffff",
                "#fafafa", "#f5f5f5", "#fafbfc", "none", "transparent"}
    if fill in bg_fills:
        # Only if it's large enough to be a group (area heuristic)
        if box.width > 250 and box.height > 150:
            return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def check_layer_structure(root) -> list[Issue]:
    """Check that the SVG uses the mandatory layered structure.

    Required order: <defs>, #background, #containers, #nodes, #labels, #connections.
    Arrows must only appear inside #connections. Rects (non-background, non-marker)
    must not appear inside #connections.
    """
    issues = []

    # Collect top-level <g> ids in document order
    g_ids = []
    for child in root:
        tag = strip_ns(child.tag)
        if tag == "g":
            gid = child.get("id", "")
            if gid:
                g_ids.append(gid)

    expected_layers = ["background", "containers", "nodes", "labels", "connections"]

    # Check if layered structure is used at all
    if not any(gid in expected_layers for gid in g_ids):
        issues.append(Issue(
            severity="warning",
            category="layer-structure",
            message="SVG does not use layered <g> structure",
            suggestion="Wrap elements in <g id=\"background\">, <g id=\"containers\">, "
                       "<g id=\"nodes\">, <g id=\"labels\">, <g id=\"connections\">"
        ))
        return issues

    # Check ordering of layers that are present
    present = [gid for gid in g_ids if gid in expected_layers]
    expected_order = [gid for gid in expected_layers if gid in present]
    if present != expected_order:
        issues.append(Issue(
            severity="error",
            category="layer-order",
            message=f"Layer order is [{', '.join(present)}] but must be [{', '.join(expected_order)}]",
            suggestion="Reorder <g> layers: background → containers → nodes → labels → connections"
        ))

    # Check that connections is the last layer with visible content
    if "connections" in present and present[-1] != "connections":
        issues.append(Issue(
            severity="error",
            category="layer-order",
            message="#connections is not the last layer — arrows may be hidden behind boxes",
            suggestion="Move <g id=\"connections\"> to be the last <g> in the SVG"
        ))

    # Find the #connections group and check for misplaced elements
    connections_g = None
    non_connections_gs = []
    for child in root:
        tag = strip_ns(child.tag)
        if tag == "g":
            gid = child.get("id", "")
            if gid == "connections":
                connections_g = child
            elif gid in ("nodes", "containers", "labels", "background"):
                non_connections_gs.append(child)

    # Check: no arrows outside #connections
    if connections_g is not None:
        for g in non_connections_gs:
            gid = g.get("id", "")
            for elem in g.iter():
                elem_tag = strip_ns(elem.tag)
                if elem_tag in ("line", "polyline"):
                    # Check if it has a marker (arrow indicator)
                    if elem.get("marker-end") or elem.get("marker-start"):
                        issues.append(Issue(
                            severity="error",
                            category="layer-violation",
                            message=f"Arrow <{elem_tag}> found inside #{gid} — arrows must be in #connections",
                            suggestion=f"Move this <{elem_tag}> into <g id=\"connections\">"
                        ))
                elif elem_tag == "path":
                    fill = (elem.get("fill") or "").lower()
                    if fill in ("none", "") and (elem.get("marker-end") or elem.get("marker-start")):
                        issues.append(Issue(
                            severity="error",
                            category="layer-violation",
                            message=f"Arrow <path> found inside #{gid} — arrows must be in #connections",
                            suggestion="Move this <path> into <g id=\"connections\">"
                        ))

        # Check: no rect nodes inside #connections
        for elem in connections_g.iter():
            elem_tag = strip_ns(elem.tag)
            if elem_tag == "rect":
                issues.append(Issue(
                    severity="error",
                    category="layer-violation",
                    message="<rect> found inside #connections — nodes must be in #nodes or #containers",
                    suggestion="Move this <rect> out of <g id=\"connections\">"
                ))

    return issues


def validate(filepath: str) -> tuple[list[Issue], dict]:
    data = parse_svg(filepath)
    issues = []

    issues.extend(check_layer_structure(data["root"]))
    issues.extend(check_box_overlaps(data["boxes"]))
    issues.extend(check_text_overflow(data["boxes"], data["texts"]))
    issues.extend(check_text_overlaps(data["texts"]))
    issues.extend(check_arrow_through_box(data["lines"], data["boxes"]))
    issues.extend(check_arrow_through_text(data["lines"], data["texts"]))
    issues.extend(check_arrow_endpoints(data["lines"], data["boxes"]))
    issues.extend(check_missing_markers(data["markers_defined"], data["markers_used"]))
    issues.extend(check_spacing(data["boxes"]))
    issues.extend(check_viewbox(data))
    issues.extend(check_grid_alignment(data["boxes"]))
    issues.extend(check_short_arrows(data["lines"]))

    return issues, data


def print_report(filepath: str, issues: list[Issue], data: dict = None, verbose: bool = False):
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    print(f"\n{'='*60}")
    print(f"  SVG Validation: {os.path.basename(filepath)}")
    print(f"{'='*60}")

    if verbose and data:
        content_boxes = _get_content_boxes(data["boxes"])
        group_boxes = [b for b in data["boxes"] if b not in content_boxes]
        print(f"\n  Parsed elements:")
        print(f"    Content boxes: {len(content_boxes)}")
        print(f"    Group boxes:   {len(group_boxes)}")
        print(f"    Text elements: {len(data['texts'])}")
        print(f"    Connections:   {len(data['lines'])}")
        print(f"    Markers:       {len(data['markers_defined'])} defined, {len(data['markers_used'])} used")
        print(f"    ViewBox:       {data['viewbox']}")

    if not issues:
        print("\n  PASS: All checks passed!\n")
        return

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for i, issue in enumerate(errors, 1):
            print(f"  {i}. [{issue.category}] {issue.message}")
            if issue.suggestion:
                print(f"     FIX: {issue.suggestion}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for i, issue in enumerate(warnings, 1):
            print(f"  {i}. [{issue.category}] {issue.message}")
            if issue.suggestion:
                print(f"     FIX: {issue.suggestion}")

    print(f"\n  Result: {'FAIL' if errors else 'WARN'} — {len(errors)} error(s), {len(warnings)} warning(s)")
    print()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    verbose = "--verbose" in flags or "-v" in sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(1)

    target = args[0]
    all_issues = []

    if os.path.isdir(target):
        svg_files = []
        for root, _, files in os.walk(target):
            for f in files:
                if f.endswith(".svg"):
                    svg_files.append(os.path.join(root, f))
        if not svg_files:
            print(f"No .svg files found in {target}")
            sys.exit(1)
        for fp in sorted(svg_files):
            try:
                issues, data = validate(fp)
                all_issues.extend(issues)
                print_report(fp, issues, data, verbose)
            except ET.ParseError as e:
                print(f"\n  ERROR: Failed to parse {fp}: {e}")
                all_issues.append(Issue("error", "parse", str(e)))
    else:
        try:
            issues, data = validate(target)
            all_issues = issues
            print_report(target, issues, data, verbose)
        except ET.ParseError as e:
            print(f"\n  ERROR: Failed to parse {target}: {e}")
            sys.exit(2)

    errors = [i for i in all_issues if i.severity == "error"]
    if errors:
        sys.exit(2)
    elif all_issues:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

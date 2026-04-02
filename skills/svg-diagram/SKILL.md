---
name: svg-diagram
description: "IMPORTANT: This skill MUST be used for ANY request involving diagrams, visualizations, or architecture drawings. It contains the color palette, layout rules, GitHub-safe SVG constraints, and templates needed to produce correct output. Without this skill, you will produce ASCII art or broken SVGs. Use this skill when: (1) user says draw, visualize, diagram, illustrate, or 'show me how X works', (2) creating architecture/flow/sequence/component/boot-flow diagrams, (3) updating ARCHITECTURE.md or any doc that needs a visual, (4) any time a diagram would communicate better than text. Covers: architecture diagrams, flowcharts, sequence diagrams, component diagrams, data flow, network topology, memory maps, boot flows, pipeline visualizations. Always output .svg files, never ASCII art."
---

# SVG Diagram Generator

Generate standalone `.svg` files that render cleanly on GitHub, GitLab, and in any browser. The diagrams should look professional and communicate system structure at a glance.

## When to use

- User asks for an architecture diagram, flowchart, sequence diagram, or component diagram
- Creating or updating documentation (ARCHITECTURE.md, README.md, etc.) that describes system structure
- Any time a visual would communicate better than text or ASCII art
- User says "draw", "visualize", "diagram", "illustrate", or "show me how X works"

## Design principles

SVG diagrams need to work everywhere — GitHub strips JavaScript, `<foreignObject>`, and external references. Stick to basic SVG elements that render universally.

**Allowed elements:** `<rect>`, `<circle>`, `<ellipse>`, `<line>`, `<polyline>`, `<polygon>`, `<path>`, `<text>`, `<tspan>`, `<g>`, `<defs>`, `<marker>`, `<linearGradient>`, `<radialGradient>`, `<filter>` (simple ones like drop shadow)

**Never use:** `<foreignObject>`, `<script>`, `<image>` with external URLs, `<use>` with external references, CSS `@import`, any JavaScript

## Color guidelines

Choose colors freely to best suit the diagram's content and context. The only hard rules:
- **Contrast**: ensure sufficient contrast between text and its background (light text on dark fills, dark text on light fills)
- **Consistency within a diagram**: use the same color for the same semantic role (e.g., all storage nodes share one color)
- **Stroke colors** should be a darker shade of the fill color for visual cohesion

## CRITICAL: Planning before drawing

**Before writing any SVG, you MUST plan the layout on paper (in your thinking).** This is the single most important step to avoid overlaps and messy diagrams.

### Step 1: Inventory
List every box, label, and connection. Count them.

### Step 2: Grid placement
Assign each component to a grid cell. Use a coordinate system:
- Define COLUMN positions (x-centers): col1=150, col2=350, col3=550, col4=750, etc. (200px apart minimum)
- Define ROW positions (y-centers): row1=80, row2=200, row3=320, row4=440, etc. (120px apart minimum)
- Place each component at a (col, row) intersection

### Step 3: Size boxes to fit text
- **Estimate text width: count characters × 9px for 14px font, × 10px for 16px font, × 7px for 12px font**
- Box width = text width + 40px padding (20px each side)
- Box height = 44px for single-line labels, +20px per additional line
- **Minimum box size: 120×44**
- If a label is long, either abbreviate it or widen the box — never let text overflow

### Step 4: Route connections
- List every connection as (source, target, label)
- Connections between vertically adjacent boxes: straight vertical line from bottom-center of source to top-center of target
- Connections between horizontally adjacent boxes: straight horizontal line from right-center of source to left-center of target
- **Non-adjacent or crossing connections: use orthogonal (right-angle) paths with `<path>` and explicit waypoints — NEVER diagonal lines that cross boxes**
- If two arrows would overlap, offset them by 15px horizontally or vertically

### Step 5: Calculate canvas size
- width = rightmost box right edge + 40px margin
- height = bottommost box bottom edge + 40px margin
- Add extra space if there are edge labels or annotations

## Layout rules (MANDATORY)

These rules are non-negotiable. Violating them produces unreadable diagrams.

### Text overlap prevention
1. **Never place text outside its containing box.** Every `<text>` element inside a box must have coordinates that fall within the box boundaries with at least 10px margin.
2. **Use `text-anchor="middle"` and center text at the box's center point** (box_x + box_width/2, box_y + box_height/2 + 5). The +5 compensates for font baseline.
3. **For multi-line text, use `<tspan>` elements** with `dy="1.2em"` and center the first line higher: box_y + box_height/2 - (line_count-1) × 8.
4. **Edge labels on arrows** must be placed at the midpoint of the line, offset by 12px perpendicular to the line direction (left/above for horizontal lines, right for vertical lines). Use `font-size="11"` for edge labels to avoid crowding.
5. **Never place two text elements closer than 20px apart** unless they are inside different boxes.

### Arrow and line precision
1. **Arrows must start and end at box edges, not at box centers.** Calculate the exact connection point:
   - Top connection: (box_x + box_width/2, box_y)
   - Bottom connection: (box_x + box_width/2, box_y + box_height)
   - Left connection: (box_x, box_y + box_height/2)
   - Right connection: (box_x + box_width, box_y + box_height/2)
2. **Leave 2px gap between arrow endpoint and box edge** to prevent the arrowhead from overlapping the box stroke. So actual coordinates are: top_y + 2, bottom_y - 2, left_x + 2, right_x - 2 for the starts, and exact edge for marker-end (refX on the marker handles this).
3. **Arrows must NEVER pass through a box.** If a straight line between source and target would cross another box, route around it using an orthogonal path:
   ```xml
   <path d="M startX startY L startX midY L endX midY L endX endY"
         fill="none" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
   ```
4. **Arrows must NEVER pass through a text label.** Since `#connections` renders on top of `#labels`, any arrow crossing a label area will obscure the text. For every arrow, verify that its path does not intersect the bounding box of any text element. If it would, offset the arrow horizontally or route around the label.
5. **Minimum arrow length: 30px.** If two connected boxes would be closer than 30px, increase spacing.
6. **For bidirectional arrows**, use two separate lines offset by 8px rather than a single double-headed arrow.
7. **Arrow marker refX must account for stroke-width.** Use `refX="9"` for `stroke-width="2"` to avoid the arrowhead overlapping the target box.

### Spacing and positioning
1. **Use a strict grid.** All box x-positions must be multiples of a consistent column width. All y-positions must be multiples of a consistent row height.
2. **Minimum gaps:**
   - 60px vertical gap between rows (edge to edge, not center to center)
   - 60px horizontal gap between columns (edge to edge)
   - 80px between group boundaries
3. **Boxes in the same row must share the same y-coordinate and height.**
4. **Boxes in the same column must share the same x-coordinate and width** (when possible).
5. **Group boxes (background rectangles) must have 20px padding** around all contained elements.

### Font and text rules
- **Font:** `font-family="Arial, Helvetica, sans-serif"` — universally available
- **Font sizes:** 14-16px for component labels, 11-12px for annotations/edge labels, 18-20px for titles, 13px for subtitles
- **NEVER use font-size larger than 16px inside boxes** — it causes overflow on longer labels
- **Bold text is ~10% wider** — account for this when sizing boxes
- **All text must use `dominant-baseline="central"` or manual baseline adjustment (+5px to y for `text-anchor="middle"`)** to vertically center in boxes

## SVG layered structure (MANDATORY)

Every SVG MUST use this layered structure. Layers are rendered in document order (first = bottom, last = top). **Connections MUST be in the last visible layer** so arrows are never hidden behind boxes.

**Violating this layer order is a generation failure. Do not interleave nodes and edges.**

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 WIDTH HEIGHT" width="WIDTH" height="HEIGHT">

  <!-- Layer 0: Definitions (markers, gradients, filters) -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
    <marker id="arrowhead-reverse" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto">
      <polygon points="10 0, 0 3.5, 10 7" fill="#4A5568"/>
    </marker>
  </defs>

  <!-- Layer 1: Background -->
  <g id="background">
    <rect x="0" y="0" width="WIDTH" height="HEIGHT" fill="#FFFFFF"/>
  </g>

  <!-- Layer 2: Containers (group/zone backgrounds) -->
  <g id="containers">
    <!-- Light-filled rounded rects that visually group related nodes -->
  </g>

  <!-- Layer 3: Nodes (component boxes) -->
  <g id="nodes">
    <!-- All <rect> component boxes here — no arrows -->
  </g>

  <!-- Layer 4: Labels (all text) -->
  <g id="labels">
    <!-- Title, group labels, node labels, annotations -->
  </g>

  <!-- Layer 5: Connections (ALL arrows — MUST be last visible layer) -->
  <g id="connections">
    <!-- Every <line> and <path> connector goes here -->
    <!-- Rendered on top of everything — never hidden behind a box -->
  </g>

</svg>
```

### Layer rules

| Layer | Contains | Order |
|-------|----------|-------|
| `<defs>` | Markers, gradients, filters | 0 (not rendered) |
| `#background` | Canvas fill, watermarks | 1 (bottom) |
| `#containers` | Group/zone background rects | 2 |
| `#nodes` | Component boxes (`<rect>`) | 3 |
| `#labels` | All `<text>` elements | 4 |
| `#connections` | All arrows (`<line>`, `<path>`) | 5 (top) |

- **NEVER place a `<line>` or arrow `<path>` inside `#nodes`, `#containers`, or `#labels`.**
- **NEVER place a `<rect>` node inside `#connections`.**
- Text labels go in `#labels`, even if they annotate an arrow (edge labels).
- If a highlight/overlay layer is needed, add `<g id="highlights">` after `#connections`.

Set `viewBox` and `width`/`height` to the actual content size. Add 30px padding around all edges.

## Diagram types

### Architecture diagram
Show components as rounded rectangles, grouped into layers (e.g., "User Layer", "Application Layer", "Data Layer"). Use vertical stacking for layers, with arrows showing data flow between them.
- Layer background: light-colored rounded rect with 20px padding
- Layer title: 13px bold, positioned at top-left of the layer background with 10px offset
- Components within a layer: arranged horizontally with 60px gaps

### Flow chart
Use rectangles for process steps, diamonds for decisions, rounded rectangles for start/end. Connect with arrows. Label decision branches (Yes/No, True/False).
- Decision diamonds: use `<polygon>` or rotated `<rect>`, sized at 80×80 minimum
- Branch labels: 11px, placed 8px away from the arrow start, on the side of the arrow

### Sequence diagram
Vertical lifelines with horizontal arrows between participants. Time flows downward.
- Participant boxes: top-aligned, minimum 100px wide, sized to text
- Lifelines: dashed vertical lines (`stroke-dasharray="6,4"`) from bottom of participant box
- Message arrows: horizontal, solid for calls, dashed for responses
- **Lifeline spacing: minimum 160px between centers** to leave room for message labels
- Message labels: 12px, placed 6px above the arrow line, centered on the arrow
- Self-calls: small loop to the right of the lifeline (15px offset)

### Component diagram
Show system components as boxes with ports/interfaces. Use different colors per component type. Show connections between interfaces.

### Boot flow / Pipeline
Vertical chain of stages with arrows between them. Each stage is a box with the component name. Use color to show different security domains or processors.
- All boxes same width, center-aligned on a single column
- Vertical arrows between each stage, exactly center-aligned
- Side annotations (optional): 12px text, positioned 20px to the right of the boxes

## Complex diagram strategies

For diagrams with more than 8 components:
1. **Use grouping aggressively.** Cluster related components into background rectangles.
2. **Reduce font to 14px** for component labels to allow narrower boxes.
3. **Use abbreviations** in boxes, with a legend below the diagram if needed.
4. **Limit connections shown.** Only draw the most important data flows. Use a note to mention omitted connections.
5. **Consider splitting** into multiple diagrams rather than cramming everything into one.

For diagrams with many crossing connections:
1. **Reorder columns/rows** to minimize crossings. Components that communicate most should be adjacent.
2. **Use curved paths** (`Q` or `C` commands in `<path>`) for connections that must cross, so they are visually distinguishable from straight orthogonal routes.
3. **Color-code connections** when multiple flows exist (use palette colors, not random colors).
4. **Add 3px gap** where one line crosses another (break the background line briefly).

## Self-check before output

Before writing the final SVG, verify:
- [ ] **Layer structure**: `<defs>` → `#background` → `#containers` → `#nodes` → `#labels` → `#connections`
- [ ] **No interleaving**: zero `<line>`/`<path>` arrows outside `#connections`; zero `<rect>` nodes outside `#nodes`/`#containers`
- [ ] Every text label fits within its box (character_count × px_per_char + 40 < box_width)
- [ ] No two boxes overlap (check x, y, width, height boundaries)
- [ ] Every arrow starts at a box edge and ends at a box edge
- [ ] No arrow passes through an intermediate box
- [ ] Grid alignment is consistent (same-row boxes share y, same-column boxes share x)
- [ ] Canvas size matches actual content bounds + 30px padding
- [ ] All arrowheads are visible (refX set correctly)
- [ ] Edge labels don't overlap with boxes or other labels

## MANDATORY: Post-generation validation

After writing every SVG file, you MUST run the validator:

```bash
python3 scripts/validate_svg.py <path-to-svg> --verbose
```

The validator checks for all the layout issues described above:
- **box-overlap**: Two content boxes occupy the same space
- **text-overflow**: Text extends beyond its containing box
- **text-overlap**: Two text elements overlap each other
- **arrow-through-box**: An arrow passes through a box it shouldn't
- **arrow-through-text**: An arrow passes through a text label area
- **arrow-endpoint**: Arrow doesn't start/end at box edge
- **missing-marker**: Arrowhead marker referenced but not defined
- **tight-spacing**: Boxes are too close together (< 30px)
- **viewbox**: Canvas doesn't match content bounds
- **grid-alignment**: Boxes at nearly-same positions (misaligned)
- **short-arrow**: Arrow too short for arrowhead to render

**Exit codes:** 0 = pass, 1 = warnings only, 2 = errors found

### Validation loop

If the validator reports errors:
1. Read the error messages and FIX suggestions
2. Edit the SVG to fix each issue
3. Re-run the validator
4. Repeat until exit code is 0 (all pass) or 1 (warnings only — acceptable)

**Do not skip validation.** Do not present the diagram to the user without running the validator first.

## MANDATORY: Visual self-review

After structural validation passes, you MUST visually inspect the rendered diagram. This catches aesthetic issues that structural checks cannot: awkward proportions, unbalanced spacing, label readability, arrow clarity.

### Steps

1. **Render** the SVG to PNG:
   ```bash
   python3 scripts/render_svg.py <path-to-svg>
   ```
   This produces a 2x PNG next to the SVG file (e.g., `diagram.svg` → `diagram.png`).

2. **Read the PNG** using the Read tool to visually inspect the rendered diagram.

3. **Check for visual issues:**
   - Text readability — not too small, not clipped, clearly legible
   - Arrow clarity — visible arrowheads, clear direction of flow
   - Balanced spacing — no lopsided gaps, even distribution
   - Overall proportions — not too tall/narrow, not cramped
   - Label-arrow separation — arrows don't visually crowd labels
   - Group container fit — no excessive empty space inside containers
   - Color contrast — text readable against its background
   - Professional appearance — would this look good in a presentation?

4. **If issues found:** edit the SVG, re-run structural validation, re-render, re-inspect.

5. **Only present to the user after visual check passes.**

### Closing the loop

When you fix a visual issue, consider whether it reveals a gap in the structural rules above. If so, note the pattern — it may become a new planning rule or validator check that prevents the issue in future diagrams.

## Output

1. Write the `.svg` file to the appropriate location (next to the markdown that references it, or in an `assets/` or `docs/` directory)
2. Run `python3 scripts/validate_svg.py <file> --verbose` and fix any errors
3. Run `python3 scripts/render_svg.py <file>` to render PNG
4. Read the PNG with the Read tool — visually inspect and fix any issues
5. Provide the markdown embed snippet: `![Description](relative/path/to/diagram.svg)`
6. Briefly describe what the diagram shows and the validation result

## Example

For a request like "draw the boot flow for TF-A → U-Boot → Linux":

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 380" width="300" height="380">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
  </defs>

  <g id="background">
    <rect x="0" y="0" width="300" height="380" fill="#FFFFFF"/>
  </g>

  <g id="containers">
    <!-- (none in this simple example) -->
  </g>

  <g id="nodes">
    <rect x="60" y="50" width="180" height="46" rx="8" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
    <rect x="60" y="136" width="180" height="46" rx="8" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
    <rect x="60" y="222" width="180" height="46" rx="8" fill="#E8854A" stroke="#C46A2F" stroke-width="2"/>
    <rect x="60" y="308" width="180" height="46" rx="8" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  </g>

  <g id="labels">
    <text x="150" y="28" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
          font-size="18" font-weight="bold" fill="#1A202C">Boot Flow</text>
    <text x="150" y="78" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
          font-size="14" font-weight="bold" fill="#FFFFFF">TF-A BL1</text>
    <text x="150" y="164" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
          font-size="14" font-weight="bold" fill="#FFFFFF">TF-A BL2</text>
    <text x="150" y="250" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
          font-size="14" font-weight="bold" fill="#FFFFFF">U-Boot</text>
    <text x="150" y="336" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
          font-size="14" font-weight="bold" fill="#FFFFFF">Linux Kernel</text>
  </g>

  <g id="connections">
    <line x1="150" y1="96" x2="150" y2="136" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
    <line x1="150" y1="182" x2="150" y2="222" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
    <line x1="150" y1="268" x2="150" y2="308" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>
  </g>
</svg>
```

Key things this example demonstrates:
- **Layered structure**: `<defs>` → `#background` → `#containers` → `#nodes` → `#labels` → `#connections`
- **No interleaving**: all rects together, all text together, all arrows together
- **Connections last**: arrows render on top, never hidden behind a box
- Boxes are consistently sized (180×46) and grid-aligned (all at x=60)
- Text is centered at (box_x + box_width/2, box_y + box_height/2 + 5)
- Arrows connect from exact bottom edge to exact top edge
- 40px gap between boxes, canvas sized to content with 30px padding

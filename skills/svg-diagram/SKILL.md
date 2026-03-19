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

## Color palette

Use this palette for consistency across diagrams. The colors are chosen for contrast on both light and dark backgrounds.

```
Primary blue:    #4A90D9 (fill), #2D6CB4 (stroke)
Secondary teal:  #50B5A9 (fill), #3A8F85 (stroke)
Accent orange:   #E8854A (fill), #C46A2F (stroke)
Accent purple:   #8B6BB5 (fill), #6B4E91 (stroke)
Neutral gray:    #6B7B8D (fill), #4A5568 (stroke)
Light fill:      #F0F4F8 (background), #E2E8F0 (alt background)
Dark text:       #1A202C
Light text:      #FFFFFF (on dark fills)
Success green:   #48BB78 (fill), #2F855A (stroke)
Warning red:     #F56565 (fill), #C53030 (stroke)
Arrow/line:      #4A5568
```

Assign colors by role: blue for compute/processing, teal for storage/data, orange for external/user-facing, purple for security, gray for infrastructure. This makes diagrams self-documenting.

## Layout guidelines

Good layout makes the difference between a clear diagram and a confusing one.

- **Flow direction:** Top-to-bottom for boot/startup flows, left-to-right for data flows and pipelines
- **Spacing:** Minimum 40px between components, 80px between groups/layers
- **Box sizing:** Minimum 120x50 for component boxes, text should have 16px padding on all sides
- **Font:** Use `font-family="Arial, Helvetica, sans-serif"` — universally available
- **Font sizes:** 16px for component labels, 12px for annotations, 20px for titles
- **Arrows:** Use `<marker>` definitions for arrowheads, stroke-width of 2 for connections
- **Grouping:** Use light-colored rounded rectangles to group related components (layers, zones)
- **Alignment:** Center-align text in boxes, keep components on a grid

## SVG template

Start every diagram from this skeleton:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 WIDTH HEIGHT" width="WIDTH" height="HEIGHT">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
    <!-- Add gradients, filters here if needed -->
  </defs>

  <!-- Title -->
  <text x="CENTERX" y="30" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-size="20" font-weight="bold" fill="#1A202C">Diagram Title</text>

  <!-- Components go here -->

</svg>
```

Set `viewBox` and `width`/`height` to the actual content size — don't use a fixed 800x600 when the content only needs 600x400. Add 20px padding around all edges.

## Diagram types

### Architecture diagram
Show components as rounded rectangles, grouped into layers (e.g., "User Layer", "Application Layer", "Data Layer"). Use vertical stacking for layers, with arrows showing data flow between them.

### Flow chart
Use rectangles for process steps, diamonds for decisions, rounded rectangles for start/end. Connect with arrows. Label decision branches (Yes/No, True/False).

### Sequence diagram
Vertical lifelines with horizontal arrows between participants. Time flows downward. Use dashed lines for lifelines, solid arrows for synchronous calls, dashed arrows for responses.

### Component diagram
Show system components as boxes with ports/interfaces. Use different colors per component type. Show connections between interfaces.

### Boot flow / Pipeline
Vertical chain of stages with arrows between them. Each stage is a box with the component name. Use color to show different security domains or processors.

## Output

1. Write the `.svg` file to the appropriate location (next to the markdown that references it, or in an `assets/` or `docs/` directory)
2. Provide the markdown embed snippet: `![Description](relative/path/to/diagram.svg)`
3. Briefly describe what the diagram shows

## Example

For a request like "draw the boot flow for TF-A → U-Boot → Linux":

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 370" width="280" height="370">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#4A5568"/>
    </marker>
  </defs>
  <text x="140" y="30" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-size="20" font-weight="bold" fill="#1A202C">Boot Flow</text>

  <!-- BL1 -->
  <rect x="60" y="50" width="160" height="50" rx="8" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  <text x="140" y="80" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-size="16" fill="#FFFFFF">TF-A BL1</text>

  <line x1="140" y1="100" x2="140" y2="130" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>

  <!-- BL2 -->
  <rect x="60" y="130" width="160" height="50" rx="8" fill="#8B6BB5" stroke="#6B4E91" stroke-width="2"/>
  <text x="140" y="160" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-size="16" fill="#FFFFFF">TF-A BL2</text>

  <line x1="140" y1="180" x2="140" y2="210" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>

  <!-- U-Boot -->
  <rect x="60" y="210" width="160" height="50" rx="8" fill="#E8854A" stroke="#C46A2F" stroke-width="2"/>
  <text x="140" y="240" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-size="16" fill="#FFFFFF">U-Boot</text>

  <line x1="140" y1="260" x2="140" y2="290" stroke="#4A5568" stroke-width="2" marker-end="url(#arrowhead)"/>

  <!-- Linux -->
  <rect x="60" y="290" width="160" height="50" rx="8" fill="#4A90D9" stroke="#2D6CB4" stroke-width="2"/>
  <text x="140" y="320" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-size="16" fill="#FFFFFF">Linux Kernel</text>
</svg>
```

This produces a clean vertical flow with color-coded stages: purple for secure firmware, orange for bootloader, blue for the OS.

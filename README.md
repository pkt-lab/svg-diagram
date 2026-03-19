# svg-diagram

A Claude Code skill that generates clean, professional SVG architecture and flow diagrams — no ASCII art, no broken renders.

## What it does

Generates standalone `.svg` files that render cleanly on GitHub, GitLab, and any browser. Supports:

- Architecture diagrams
- Flowcharts
- Sequence diagrams
- Component diagrams
- Boot flow / pipeline visualizations
- Network topology
- Memory maps

## Why use this skill

- **GitHub-safe SVGs** — no `<foreignObject>`, no JavaScript, no external refs
- **Consistent color palette** — color-coded by role (blue=compute, teal=storage, orange=external, purple=security)
- **Professional layout** — proper spacing, alignment, fonts, arrowheads
- **Drop-in markdown embeds** — outputs `![description](path/to/diagram.svg)` ready to paste

## Install

```bash
claude skill add --from https://github.com/pkt-lab/svg-diagram
```

Or manually copy `SKILL.md` to `~/.claude/skills/svg-diagram/SKILL.md`.

## Usage

Invoke explicitly:
```
/svg-diagram Draw the boot flow from RSE → SCP → TF-A → U-Boot → Linux
```

Or just ask naturally — the skill auto-triggers on "draw", "visualize", "diagram", "illustrate":
```
Can you draw an architecture diagram of our microservices?
```

## Example output

![TC3 FVP Boot Flow](examples/tc3_boot_flow.svg)

## Color palette

| Role | Fill | Stroke | Use for |
|------|------|--------|---------|
| Primary blue | `#4A90D9` | `#2D6CB4` | Compute, processing |
| Teal | `#50B5A9` | `#3A8F85` | Storage, data |
| Orange | `#E8854A` | `#C46A2F` | External, user-facing |
| Purple | `#8B6BB5` | `#6B4E91` | Security, firmware |
| Gray | `#6B7B8D` | `#4A5568` | Infrastructure |
| Green | `#48BB78` | `#2F855A` | Success, healthy |
| Red | `#F56565` | `#C53030` | Warning, error |

## License

MIT

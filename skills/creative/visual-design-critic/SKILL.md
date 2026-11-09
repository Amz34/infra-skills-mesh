---
name: visual-design-critic
description: "Use when critiquing UI/UX layouts or URLs. Design critic."
metadata:
  tags: [design, critiquito, visual-qa, ui-ux, accessibility, figma, vision]
---

# Visual Design Critic (Critiquito Mode)

Analyzes screenshots, UI mocks, or live URLs of our enterprise websites (e.g., `imaa-kiosk.pages.dev` or `sanad.io`) to provide instant, expert-level UI/UX feedback.

## Critique Focus Areas
For every screen reviewed, critique across:
1. **Hierarchy**: Visual flow, focal points, primary vs. secondary actions.
2. **Spacing**: Grids, paddings, margins, alignment.
3. **Typography**: Font stacks, readability, line heights, sizes.
4. **Color**: Contrast, palettes, consistency, state feedback (hover, active, disabled).
5. **Copy**: Clarity, tone, microcopy, error states.
6. **Accessibility (a11y)**: Large touch targets (min 48x48px for kiosk), high contrast, RTL layout logic (Arabic support).

## Handoff Ticket Shape
Generate discrete markdown issues/tickets (for Linear, Notion, or git):
- **Title**: `<Screen Name> - <Concrete Problem in Plain Words>`
- **Severity**: `[Blocker | Major | Minor]`
- **Body**: What a user hits, where, what it costs them, the specific fix, and the severity.

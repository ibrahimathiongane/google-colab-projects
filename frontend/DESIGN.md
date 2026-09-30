# DESIGN.md — Design tokens & rules (Linear-inspired)

The app and the future landing page share one system. Everything lives in
`src/tokens.css` — **never hardcode a hex value in a component.**

## Philosophy

1. **Dark-first.** The canvas is near-black and information emerges from it
   like system signals. There is no "light theme adaptation" — light would
   be designed separately, from scratch.
2. **No decoration without purpose.** No gradient, shadow or color unless it
   carries meaning. Hierarchy comes from *hairlines* and *ink opacity*, not
   from elevation soup.
3. **Density with clarity.** 4px unit / 8px step. One intention per section,
   one primary action per view (1:1 attention ratio — critical on the
   landing page).
4. **Sentence case.** Never all-caps shouting; uppercase is reserved for
   rare eyebrows (`--tracking-wide`).

## Color

| Token | Value | Role |
|---|---|---|
| `--canvas` | `#08090a` | App background |
| `--canvas-marketing` | `#010102` | Landing page "marketing black" |
| `--surface-1/2/3` | `#0f1011` / `#141516` / `#1c1d1f` | Cards, hover, pressed |
| `--hairline` | `#23252a` | 1px separators (surgical, never heavy borders) |
| `--ink` → `--ink-30` | `#f7f8f8` @ 100/70/50/40/30% | Reading hierarchy by opacity |
| `--primary` | `#5e6ad2` | **The** accent: CTA, focus ring, brand mark |
| `--primary-hover` | `#828fff` | Hover only |
| `--success` | `#4cb782` | Done / positive — an indicator light |
| `--danger` | `#eb5757` | Destructive / errors — an indicator light |
| `--warning` | `#f2c94c` | Streaks / attention — an indicator light |

**Accent discipline:** exactly one accent. The three semantic colors appear
only as status signals (like LEDs on a device) — never as surfaces.

## Typography

- **UI/titles:** Inter Variable (self-hosted via `@fontsource-variable/inter`,
  no CDN), fallbacks `SF Pro Display, -apple-system, system-ui`.
- **Weights:** 300 → 700, default 400, emphasis 500/590. Never shouty bold.
- **Tracking:** negative on headings — `--tracking-tighter: -0.022em`
  (≥24px), `--tracking-tight: -0.014em` (16–24px).
- **Mono:** `--font-mono` (Berkeley Mono licensed stack, fallback
  `ui-monospace, SF Mono, Menlo`) for *metadata only*: metrics, badges,
  dates, cue times, keyboard hints.

## Geometry & motion

- Radii: `--radius-sm: 2px` (badges) · `--radius-md: 6px` (buttons, inputs)
  · `--radius-lg: 12px` (cards/panels). Never mix scales inside one element.
- Sections (landing): `--space-9` = 96px. App density stays at 8/16px.
- Motion: `--ease-out: cubic-bezier(0.2, 0.8, 0.2, 1)`, 120–180ms, only on
  color/border/transform — instant but fluid, native-app feel.

## Landing page (future) checklist

- Background = `--canvas-marketing`; app screenshots as the only imagery.
- One section = one claim = one CTA (`--primary`), 96px rhythm between them.
- Hero title: `--weight-semibold` + `--tracking-tighter`.
- All copy in sentence case; both locales via the existing i18n dictionaries.

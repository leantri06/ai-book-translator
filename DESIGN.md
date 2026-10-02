---
name: Editorial Workbench
colors:
  primary: "#E9E9E7"
  primary-hover: "#FFFFFF"
  surface: "#171717"
  surface-elevated: "#222222"
  background: "#111111"
  input: "#1C1C1C"
  border: "#404040"
  on-surface: "#E9E9E7"
  secondary: "#B4B4B0"
  muted: "#A0A09C"
  on-primary: "#171717"
typography:
  headline: {fontFamily: "Segoe UI, sans-serif", fontSize: 20px, fontWeight: 600, lineHeight: 1.3}
  body: {fontFamily: "Segoe UI, sans-serif", fontSize: 14px, fontWeight: 400, lineHeight: 1.6}
  label: {fontFamily: "Segoe UI, sans-serif", fontSize: 12px, fontWeight: 600, lineHeight: 1.5}
  book: {fontFamily: "Georgia, serif", fontSize: 18px, fontWeight: 400, lineHeight: 1.85}
  log: {fontFamily: "Consolas, monospace", fontSize: 12px, fontWeight: 400, lineHeight: 1.6}
rounded:
  none: 0px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.none}"
    height: 36px
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.none}"
---

# Editorial Workbench

## Overview
A focused translation and reading workspace. The document is the main visual element; controls support editing without competing for attention. Preserve the existing Vietnamese interface and all translation, glossary, export and textbook-conversion flows.

## Colors
Neutral graphite surfaces, off-white text and restrained gray borders only. Status is named in text, never conveyed by color alone. The primary action uses an off-white fill with dark text; secondary actions use solid surfaces and borders. Progress uses a single off-white fill with a visible numeric percentage, not a categorical color palette.

## Typography
Use locally available system fonts so the interface works without third-party font requests. Georgia distinguishes book content from UI. Labels are concise; avoid exaggerated claims about quality, quota or speed. Body text must meet WCAG AA contrast on its surface.

## Layout
Two-level header separates global actions from project selection and progress. Chapter navigation remains on the left; glossary is closed until requested. Studio compares paragraphs in two columns on desktop and stacked, explicitly labeled pairs on narrow screens. Reader text has a bounded measure. Drawers and modal content scroll independently without hiding their close controls.

## Elevation & Depth
Solid surfaces and one-pixel dividers define hierarchy. No shadows, glows, gradients or backdrop blur. Active navigation uses a strong edge and a quiet tonal change.

## Shapes
All UI corners are square, including buttons, fields, badges, progress tracks, panels and images. Native controls are given the same flat styling where supported.

## Components
- Buttons: short text labels, visible keyboard focus, clear disabled/loading feedback.
- Navigation: keyboard-operable chapter buttons and view tabs; accessible expanded/selected state.
- Modals: dialog semantics, focus containment, Escape dismissal, return focus to the initiating control.
- Progress: numeric labels, accessible progress values, one neutral fill. Upload indeterminate animation is subtle.
- Notices: border and explicit text, no celebratory illustrations or warning emoji.
- Quota: named states and model details, not colored dots.

## Do's and Don'ts
- Do keep every existing controller DOM id and API payload contract intact.
- Do keep headings, figures, table captions and footnotes readable.
- Do use short 120–180 ms transitions and respect reduced-motion preferences.
- Don't add decorative icons, flags, emoji, UI libraries or build dependencies.
- Don't animate document layout or continuously pulse status labels.
- Don't change source book content or exporter styling as part of the UI redesign.

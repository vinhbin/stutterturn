---
name: StutterTurn Studio
description: A cool charcoal studio workspace for inspecting voice-agent turn taking.
colors:
  accent: "#50d9f3"
  speaking: "#71e0b5"
  holding: "#f4c46a"
  agent: "#50d9f3"
  overlap: "#fb7185"
  bg: "#090e14"
  panel: "#101923"
  raised: "#172330"
  fg: "#edf4fa"
  muted: "#9cabbc"
  dim: "#8d9bad"
  silence: "#63758a"
  border: "#304154"
  rule: "#223141"
  hover: "#203247"
  selected: "#12303d"
  control-border: "#526b82"
typography:
  display:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "clamp(64px, 7.8vw, 96px)"
    fontWeight: 750
    lineHeight: 0.99
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "clamp(30px, 3vw, 42px)"
    fontWeight: 660
    lineHeight: 1.08
    letterSpacing: "-0.035em"
  introduction:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "clamp(21px, 2vw, 27px)"
    fontWeight: 520
    lineHeight: 1.35
    letterSpacing: "-0.012em"
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "'JetBrains Mono', Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
  note:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.65
rounded:
  surface: "12px"
  control: "6px"
  key: "3px"
  track: "2px"
spacing:
  control-gap: "8px"
  action-gap: "12px"
  field-gap: "16px"
  section-gap: "24px"
  hero-gap: "72px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.bg}"
    rounded: "{rounded.control}"
    padding: "11px 20px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "11px 20px"
  console-button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#06232c"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  console-button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  input-url:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "10px 11px"
  navigation:
    textColor: "{colors.muted}"
    padding: "10px 0"
  status-chip:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "7px 9px"
  monitor:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.fg}"
    rounded: "{rounded.surface}"
    padding: "18px 22px 20px"
  configuration:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "12px"
  sequence-button:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
---

# Design System: StutterTurn Studio

## Overview

**Creative North Star: "Dark studio console"**

Cool charcoal surfaces, ice cyan actions, and clear instrument labels give StutterTurn the character of a working studio. The user selected this direction on 2026-10-10, replacing the earlier warm brown and cream appearance. Controls have visible edges and clear state changes; generous landing-page type introduces the same visual language used in the denser operating console.

This is the shared visual authority for the [overview](index.html), [judge guide](judge/index.html), [live workspace](live/index.html), and [call console](demo-ui/index.html). Its tokens come from [site.css](site.css) and [console styles](demo-ui/styles.css); the [console design document](demo-ui/DESIGN.md) specializes their operating layout and event semantics. [PRODUCT.md](../PRODUCT.md) records product constraints, and the [surface brief](../.impeccable/surfaces/studio-refresh.md) records this refresh's composition. The [root v2 sidecar](../.impeccable/design.json) holds component previews and extensions; its derived tonal ramps are preview aids, not additional production colors.

**Key Characteristics:**

- Cool charcoal layers and cyan controls with visible borders.
- Large Archivo headlines balanced by precise JetBrains Mono instrumentation.
- Caller, decision, and reported audio remain distinct, labeled tracks.
- Responsive controls, keyboard access, and explicit evidence provenance.

## Colors

Cyan supplies the active voice against a cool, dark neutral range. The frontmatter is the normative palette; console-only interaction tokens are included so new surfaces share the same controls.

### Primary

- **Ice cyan — accent:** primary actions, focus, current-route marks, the brand symbol, and the illustrative playhead.
- **Ice cyan — agent:** reported agent audio on the console and the explicitly illustrative reply on the overview. It shares the accent value but keeps its separate semantic name.

### Secondary

- **Caller mint — speaking:** caller speech and connected status.
- **Holding amber — holding:** incomplete-turn decisions, holding spans, preview status, and pending evidence items.
- **Overlap rose — overlap:** console overlap state and patterned collision bands.

### Neutral

- **Cool charcoal — bg:** the page and inset fields.
- **Studio slate — panel:** monitors, toolbars, configuration tiles, and status chips.
- **Raised slate — raised:** secondary controls and selected interaction surfaces.
- **Ice white — fg:** primary text and complete-decision flags.
- **Blue gray — muted:** secondary copy, labels, and provenance.
- **Dim blue gray — dim:** unavailable console controls.
- **Silence slate — silence:** silence indicators and scrollbars.
- **Structural slate — border / rule:** panel edges and quieter internal dividers.
- **Control steel — control-border:** stronger native field and button boundaries.
- **Hover slate / selected teal — hover / selected:** console hover and checked-configuration fills.

**The Labeled State Rule.** State color always accompanies text; overlap also has a patterned band. Cyan controls do not imply reported audio.

## Typography

Archivo carries the brand, headlines, introduction, and console tally. System sans-serif carries prose and fields. JetBrains Mono carries clocks, phase labels, revisions, and event measurements. Both web fonts are local Latin-subset WOFF2 files with fallback stacks and `font-display: swap`; the assets and licenses live in [fonts/](demo-ui/fonts/).

The frontmatter records the desktop landing hierarchy. The introduction is limited to 32 characters per line and contextual copy to 55; general paragraphs have a 70-character cap. Section headings are smaller than the hero, while mono labels stay at least 11px. The console uses its own compact body and tally roles documented alongside the application.

**The Two Reading Speeds Rule.** Use Archivo and body copy to explain the task; use mono type for values that people inspect or compare.

## Layout

The overview uses a centered shell capped at 1440px with 40px desktop gutters. Its first row pairs a headline with the introduction and primary action (1.05fr / 1fr, 72px gap), followed by the wide illustrative sequence. Evidence uses two columns and open ruled rows; three numbered comparison channels lead to the final workspace action.

- At 1000px and below, hero spacing tightens and the heading uses a smaller fluid scale.
- At 720px and below, the hero, evidence, comparison, and closing sections become one reading column; overview gutters are 20px.
- At 480px and below, navigation moves below the wordmark and hero actions remain side by side, with the primary action taking the flexible space.
- The illustration retains a 520px minimum diagram width inside a horizontally scrollable, focusable region. Its visible scroll instruction appears at 640px and below.
- A sequence container query at 620px stacks the figure heading and arranges playback controls into two columns. It responds to the figure's available width.

The live workspace shell is capped at 1536px, with 32px desktop and 16px narrow-screen gutters. A compact operational introduction precedes the dominant console. The separate judge guide uses the same visual system for a guided evaluation, recorded evidence, architecture, and capability limits; it does not contain an iframe or run controls. Its primary action opens `/live/`. The legacy `/judges/` path redirects to `/judge/` and preserves query strings and fragments, with a visible fallback link without JavaScript. The console itself places source selection and transport above the monitor and right setup inspector; see its design document for breakpoints and scroll regions.

On `/live/`, [site.js](site.js) loads the same console in a same-origin iframe and adds the `embedded-console` class to its root. The console stylesheet owns the embedded layout, hides duplicate branding, retains connection status, and keeps its responsive rules active. A `ResizeObserver`, font readiness, and animation-frame batching keep frame height aligned with the content; the direct full-console link remains available.

## Elevation & Depth

Depth comes from tonal surfaces and single-pixel rules. There are no shadows, decorative glass layers, or floating evidence cards. Cyan focus outlines are 2px with a 5px offset on site controls; the console uses a 3px offset.

Site buttons change background over 140ms with ease-out and move down 1px while pressed. The illustration's JavaScript animation and the console's active holding pulse are described with their components. Cross-document view transitions appear only in [site.css](site.css), with a 160ms root transition inside `prefers-reduced-motion: no-preference`. They progressively enhance supported overview/judge/live navigation; the console has no view-transition rule. Reduced-motion styles remove CSS transitions and animations.

**The Flat Workspace Rule.** Separate working areas with tone, spacing, and borders; reserve bright color for an action or a labeled state.

## Shapes

Working panels have modest corners, controls have smaller corners, and timeline bars stay almost square. The frontmatter records these reusable steps. Small dots identify status and legend entries; the brand mark is an inline line symbol. Evidence is organized with horizontal rules and open space rather than another raised panel.

## Components

### Navigation and actions

The wordmark and cyan symbol lead a simple route navigation. The current route has a cyan underline and `aria-current`; links retain visible keyboard focus. A cyan primary action and outlined quiet action use a 48px minimum height. Hover lightens the primary and fills the quiet action. The console's Start, Stop, and Reset variants retain native button states and keyboard hints.

### Illustrative sequence

The signature figure shows caller and agent lanes, WAIT and COMPLETE flags, a playhead, a concept clock, and a phase explanation. The visible caption says that it represents no recorded timing or audio. The diagram has a complete accessible text description; decorative track internals are hidden from assistive technology.

JavaScript reveals a native Play/Pause button and range input. Scrubbing pauses playback and updates the phase, explanation, clock, and range `aria-valuetext`. The animation uses a 7.5-second cycle: 6 seconds advance through the illustration and 1.5 seconds hold the completed frame. With normal motion preference it runs only while visible; leaving the viewport or hiding the document pauses it. A user's pause is respected on return.

Reduced motion starts at the completed frame without autoplay. A user can still explicitly play or scrub; a new reduced-motion preference pauses an active sequence. Without JavaScript, the completed diagram and caption remain visible and the transport stays hidden. There is no scroll-reveal animation.

### Console toolbar, inspector, and records

The source selector sits beside the transport above the monitor. Configuration radios and connection/preview controls occupy the right inspector. Native inputs, a distinct selected fill and border, disabled states, and visible focus keep the operating controls legible. On mobile, a setup jump link reaches the inspector below the monitor.

The monitor, connection chip, synthetic banner, run record, summary, and independently scrollable ledger share this palette. Detailed behavior belongs to the [console component contract](demo-ui/DESIGN.md). Do not replace its event times with an illustrative playback clock.

### Evidence and presenter guidance

Evidence uses readable body labels, precise revision text, quiet rules, and recorded/pending dots. The overview and judge guide link to the exact [replay-v2 evidence](https://github.com/vinhbin/stutterturn/tree/9805a06/agent/evidence/2026-10-10-replay-v2); the judge page also links to the [event contract at the execution revision](https://github.com/vinhbin/stutterturn/blob/bcf50d1/agent/CONTRACT.md). The evidence artifact is pinned to `9805a06`; its five recordings and ten stock/patient logs were executed on `bcf50d1`.

Keep the source revision, unreviewed-label caveat, and playback qualification with the evidence. The browser plays no audio. Candidate availability comes from the connected backend. A decision, reported audio receipt, verified speaker playback, and an efficacy claim are different facts. The presenter guide uses native disclosure to keep guidance accessible without crowding the workspace.

## Do's and Don'ts

### Do:

- **Do** use the shared cool charcoal palette and cyan control hierarchy.
- **Do** keep labels, focus, native controls, and horizontal-scroll access intact.
- **Do** keep illustration, synthetic preview, and backend evidence visibly distinct.
- **Do** keep replay provenance and playback limitations beside the corresponding data.

### Don't:

- **Don't** reintroduce the superseded warm brown and cream visual world.
- **Don't** turn illustrative proportions into recorded timings or add invented waveforms.
- **Don't** use color alone to communicate caller, holding, audio, or overlap state.
- **Don't** imply that a turn decision or received audio verifies speaker playback.

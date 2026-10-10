---
name: StutterTurn Call Console
description: A cool charcoal studio console for timestamped caller and agent events.
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
    fontSize: "64px"
    fontWeight: 760
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  brand:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "28px"
    fontWeight: 750
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.5
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  measurement:
    fontFamily: "'JetBrains Mono', Consolas, monospace"
    fontSize: "28px"
    fontWeight: 400
    lineHeight: 1.2
  label:
    fontFamily: "'JetBrains Mono', Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
  note:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  surface: "12px"
  control: "6px"
  phase: "4px"
  key: "3px"
  flag: "2px"
spacing:
  control-gap: "8px"
  field-gap: "16px"
  workspace-gap: "20px"
  record-gap: "24px"
  support-gap: "28px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#06232c"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  input-url:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "10px 11px"
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
  setup-navigation:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
---

# Design System: StutterTurn Call Console

## Overview

**Creative North Star: "Dark studio console"**

A cool charcoal operating workspace with cyan transport controls, semantic event color, and explicit provenance. Source selection and run transport sit above the main monitor; configuration and connection controls sit in a right inspector. The large tally and shared timeline provide an immediate reading while the run record and ledger keep the underlying events inspectable.

This document specializes the [shared studio design](../DESIGN.md), selected on 2026-10-10. It records [styles.css](styles.css), [index.html](index.html), and [app.js](app.js). The [root sidecar](../../.impeccable/design.json) describes the complete visual system; the [console sidecar](.impeccable/design.json) contains its local component previews. Derived preview ramps do not add production tokens.

**Key Characteristics:**

- Source and transport above a dominant event monitor.
- A right setup inspector with native configuration and connection controls.
- Precise source-relative time, readable overflow, and visible provenance.
- Cool tonal layers, cyan focus, and labeled semantic state color.

## Colors

The frontmatter matches the console's current CSS custom properties. Ice cyan is the primary action and focus color; ice white remains the main text color.

### Primary

- **Ice cyan — accent:** Start, focus, selected configuration borders, controls, and links.
- **Ice cyan — agent:** backend-reported agent audio, qualified as unverified playback.

### Secondary

- **Caller mint — speaking:** caller speech and the connected-status dot.
- **Holding amber — holding:** incomplete decisions, holding spans, and preview status.
- **Overlap rose — overlap:** the interrupted tally and patterned overlap region.

### Neutral

Cool charcoal, studio slate, and raised slate supply the canvas, monitor, and controls. Ice white is primary text; blue gray is supporting text; dim blue gray marks unavailable options. Silence slate supports neutral state and scrollbars. Structural slate divides sections, control steel strengthens fields, and hover slate and selected teal distinguish interactive states.

**The Labeled State Rule.** Every semantic color has a text label; overlap also uses hatching and an onset marker when its end is unknown.

## Typography

Archivo supplies the identity, headings, configuration names, and uppercase state tally. System sans-serif carries controls and explanations. JetBrains Mono carries source-relative times, measurements, event probabilities, and compact labels. Local WOFF2 fonts and fallback stacks avoid a remote font dependency; licenses and source hashes are in [fonts/](fonts/).

The frontmatter gives base roles. The tally grows to 78px at 1440px and above. At 1100px and below, or when the monitor container is no wider than 610px, it becomes 54px; at 560px and below it becomes 49px. The longer interrupted label uses 66px, 44px, and 39px at those respective sizes. The event clock is 22px at base, 20px in compact layouts, and 18px on phones; phone measurements are 21px. Instrument labels remain at least 11px, with notes and track text at 12px.

**The Event Time Rule.** The console clock follows the latest reported source timestamp. It is not an animated playback clock.

## Layout

The standalone console is centered at a maximum width of 1600px with 24px desktop side padding. A full-width toolbar pairs source selection with Start, Stop, and Reset. Beneath it, a flexible monitor and 308px setup inspector share a 20px gap. Run identity, progressively disclosed provenance, final summary, and event ledger follow in ruled sections.

- At 1100px and below: the inspector is 282px wide, the gap is 16px, and transport spacing tightens.
- At 850px and below: side padding is 18px, the toolbar stacks, the inspector moves below the monitor in two columns, and a visible Connection & configuration jump link targets its focusable container. Summary fields use three columns.
- At 560px and below: side padding is 12px, Start spans a full row above Stop and Reset, the inspector becomes one column, metadata stacks, and the summary uses two columns.
- The monitor's 610px container query wraps the tally and repositions its clock based on actual available space, including in the judge iframe.

The event timeline retains a 580px minimum canvas when populated and scrolls horizontally within the monitor. Its hint appears when content overflows; the populated chart is keyboard focusable and has an event-specific accessible description.

The ledger stays inside a region with a 780px minimum-width table and 360px maximum height. Its explanatory caption sits outside the scrolling area, column headings remain sticky, and long run identifiers wrap. At 850px and below, a visible scroll hint explains horizontal access. The region is a Tab stop once events exist; the empty table is not. Keyboard instructions for ledger scrolling are hidden while empty.

The judge host adds `embedded-console` to the iframe's root. Its CSS removes duplicate identity chrome and outer padding while preserving connection status, banners, control semantics, and all responsive rules. The host observes body size and fonts to update iframe height, so layout changes do not require a second console implementation.

## Elevation & Depth

There are no shadows. Panel fills, neutral field insets, and single-pixel borders distinguish the toolbar, monitor, configuration tiles, and records. A 2px cyan focus outline with a 3px offset makes keyboard location visible.

Buttons transition background and border over 140ms with ease-out. An open holding span pulses over 1.5 seconds only while the run is active. Reduced-motion preference disables CSS animation, transitions, and smooth scrolling. The console does not use view transitions; that progressive enhancement belongs only to the overview and judge host.

**The Flat Workspace Rule.** Separate working areas with tone, spacing, and borders; reserve bright color for an action or a labeled state.

## Shapes

Toolbar and monitor use the broadest corners; controls, chips, configuration tiles, alerts, and the timeline frame use the smaller control radius. Phase labels, keyboard hints, and event flags use tighter corners. Configuration options are individual bordered tiles. Dots and small legend marks are the exceptions to the rectangular workspace language.

## Components

### Source and transport

The native source selector carries a persistent source note. Start is the cyan primary action with a play icon and a 48px minimum height; Stop and Reset are secondary controls with a 44px minimum height. Visible S, X, and R hints complement the native controls. Disabled buttons use neutral surfaces and dim text. Connection actions have a compact 40px desktop height and expand to 44px on phones.

### Setup inspector

Configuration tiles retain native radios, a visible selected border and fill, availability labels, and keyboard hints. Unavailable backend candidates remain disabled. Connection & preview is a native open disclosure with a labeled URL field, Connect/Disconnect actions, and a preview checkbox. The mobile setup jump reaches this inspector without moving or duplicating its controls.

### Status and provenance

The connection chip combines text with a status dot. Development preview has a persistent light banner reading synthetic, no audio, and not benchmark evidence. Status and run alerts use polite status regions; the rapidly changing event clock does not announce continuously. Detailed model metadata and recording/integration notes remain in native disclosures.

### State tally and shared timeline

The named tally, top state rule, configuration identity, and latest event time provide the immediate readout. The caller and agent lanes share source-relative seconds, with WAIT for `turn_incomplete` and COMPLETE for `turn_complete`; probabilities appear when supplied. Agent bars begin at `agent_audio_start`, independently of a completion decision.

Holding sits beneath the caller track. Open caller/audio/holding spans retain dashed right edges and an end-unreported description, even when a run ends. An overlap uses a hatched band until a reported speech or audio end; an unknown end is an onset marker, not a fabricated duration. Synthetic and backend overlap descriptions retain their respective qualifications.

### Summary and ledger

Turn complete, reported agent audio, and decision-to-audio delay remain separate measurements. The ledger carries run/configuration attribution, source time, event, detail, probability, and model. Missing values remain missing. A fresh run clears the prior event table; final summary values come from the backend.

The overview and judge host supply the pinned [replay-v2 handoff](https://github.com/vinhbin/stutterturn/tree/9805a06/agent/evidence/2026-10-10-replay-v2) and [event contract](https://github.com/vinhbin/stutterturn/blob/bcf50d1/agent/CONTRACT.md). The console does not convert that handoff into a new live-run result. Received backend audio is not verified speaker playback, and the browser plays no audio.

## Do's and Don'ts

### Do:

- **Do** keep source selection, transport, setup access, and provenance easy to find.
- **Do** preserve native controls, visible focus, shortcuts, and reduced-motion behavior.
- **Do** label fixture views synthetic, no audio, and not evidence.
- **Do** keep scrollable timeline and ledger content reachable by keyboard.

### Don't:

- **Don't** reintroduce warm neutral tokens or a monochrome primary transport.
- **Don't** draw a waveform without real waveform data.
- **Don't** give an unknown interval a known endpoint or duration.
- **Don't** present backend audio receipt as verified speaker playback.

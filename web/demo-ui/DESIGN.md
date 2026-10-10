---
name: StutterTurn Call Console
description: A broadcast console for timestamped caller and agent events, with explicit provenance.
colors:
  bg: "#0c0a09"
  panel: "#171412"
  raised: "#201c19"
  fg: "#f5f4f2"
  muted: "#aaa29a"
  dim: "#827b74"
  border: "#39332e"
  rule: "#2a2521"
  speaking: "#30d158"
  silence: "#57534e"
  holding: "#f59e0b"
  agent: "#38bdf8"
  overlap: "#ef4444"
typography:
  display:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "64px"
    fontWeight: 760
    lineHeight: 0.95
    letterSpacing: "-0.035em"
  brand:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
    fontSize: "32px"
    fontWeight: 780
    lineHeight: 1
    letterSpacing: "-0.035em"
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
  monitor: "14px"
  control: "4px"
  key: "3px"
  timeline: "2px"
spacing:
  control-gap: "8px"
  desk-section: "20px"
  column-gap: "28px"
  record-section: "30px"
components:
  button-primary:
    backgroundColor: "{colors.fg}"
    textColor: "{colors.bg}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.fg}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
  chip:
    textColor: "{colors.fg}"
    padding: "5px 8px"
  monitor:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.fg}"
    rounded: "{rounded.monitor}"
    padding: "22px 26px 20px"
---

# Design System: StutterTurn Call Console

## Overview

**Creative North Star: "Broadcast console"**

A warm near-black operating console with monochrome controls and semantic state color. The large tally, timestamped caller/agent tracks and nearby run controls support a short laptop demonstration; detailed provenance and the event ledger sit below the main interaction.

**Key Characteristics:**

- Large state tally; precise event time.
- Flat surfaces, restrained corners and visible borders.
- Synthetic and unverified playback status remain explicit.

This records the implemented system in [styles.css](styles.css), [index.html](index.html) and [app.js](app.js). Frontmatter contains actual base tokens and extracted component values; responsive overrides are described below. The [v2 sidecar](.impeccable/design.json) adds component previews, motion and breakpoints without inventing color ramps.

## Colors

Warm white is the primary control color. Near-black canvas, two surface tones, muted text and quiet rules keep the surrounding chrome neutral. The `dim` token is defined but not used by current component rules; secondary text uses `muted`.

Semantic accents carry state: green for caller speech, amber for holding/incomplete decisions, cyan for reported agent audio and red for reported overlap. Silence stays neutral. Labels accompany color; overlap also uses a hatched band. A connected indicator uses green, while error text uses the stylesheet's lighter red treatments.

## Typography

Archivo supplies the wordmark, headings and uppercase state tally; system fonts carry body text; JetBrains Mono carries timestamps, measurements and compact instrumentation. Both web fonts load from local Latin-subset WOFF2 files with system fallbacks. Licenses and source hashes live in [fonts/](fonts/).

The frontmatter describes base roles. The tally expands to 82px at the large-display breakpoint, becomes 55px on compact desktop, returns to 64px when the console stacks, and becomes 52px on phones. The longer interruption label uses smaller state-specific sizes. Phone measurements use 21px; the event clock uses tabular numbers and follows the latest reported timestamp, with no simulated playback clock. Timeline lane/ruler labels use 11px; decision flags, track text, notes and provenance use 12px. These remain readable on the phone layout rather than shrinking into microtype.

## Layout

The centered shell is capped at 1600px, with 32px desktop side padding. The primary grid pairs a flexible monitor with a 332px control desk and 28px gap. Supporting records use ruled sections rather than a repeated card grid.

- At 1100px and below: 24px side padding, 290px desk and 20px grid gap.
- At 850px and below: monitor above a two-column control desk; summary fields use three columns.
- At 560px and below: 16px side padding, one-column controls and metadata, two-column summary, and a 12px monitor radius.
- At 1440px and above: a larger tally uses the available monitor space.

The timestamped timeline scrolls horizontally when needed; its canvas has a 580px minimum and a visible scroll hint when it overflows. The event ledger scrolls independently with sticky headings and a 780px minimum table width. Neither should force the entire page wider than the viewport.

## Elevation & Depth

There are no shadows. Surface tones and single-pixel borders separate the monitor, controls and supporting records. A bright focus outline establishes keyboard location without adding ornamental depth. Button backgrounds transition over 140ms with ease-out. An open holding span pulses over 1.5 seconds only while the run is active; reduced-motion preference disables transitions and animations.

## Shapes

The monitor has the broadest corners; controls, phase labels and keyboard hints use restrained corners. Timeline bars are nearly square. Configuration options form one joined list with corners only at its ends. Circular status dots are the small exception to the rectangular instrument language.

## Components

- **Run controls:** the full-width warm-white start action leads; Stop and Reset share the secondary treatment. Disabled controls remain visibly unavailable. Focus uses a 2px warm-white outline with 4px offset.
- **Fields and configurations:** native selectors, radios and URL input retain keyboard behavior. Checked configurations change neutral fill and border; unavailable candidates stay disabled.
- **Status and provenance:** the connection chip, persistent synthetic banner, playback note and per-run metadata distinguish fixture data from backend reports. The banner uses high-contrast monochrome styling rather than a state accent.
- **State tally:** a large named state and matching top rule provide the immediate readout, with configuration identity directly beneath. Reported overlap stays qualified as synthetic or playback-unverified.
- **Shared timeline:** caller and agent lanes share source-relative seconds and decision flags. `turn_incomplete` is WAIT; `turn_complete` is COMPLETE; flags include probability when supplied. An amber holding span sits below the caller bar. Agent bars start only at `agent_audio_start`. A reported overlap spans both lanes until a reported speech or audio end; an unknown overlap end is an onset marker, not an invented duration. Open caller/audio/holding spans have dashed right edges and an “end not reported” description, including after a run ends.
- **Ledger and summary:** timestamps, run/configuration attribution and final backend values remain inspectable. Missing values stay missing; detailed metadata is progressively disclosed with native details controls.

## Do's and Don'ts

- Do keep state names, timestamps and provenance visible alongside semantic color.
- Do preserve native controls, visible focus, keyboard shortcuts and reduced-motion behavior.
- Do label every fixture view synthetic, no audio and not evidence.
- Don't draw a waveform without real waveform data.
- Don't give an unknown interval a known endpoint or duration.
- Don't present received backend audio as verified speaker playback.

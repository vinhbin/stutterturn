---
name: StutterTurn Site Extension
description: Landing and judge routes extending the existing broadcast console.
colors:
  bg: "#0c0a09"
  panel: "#171412"
  raised: "#201c19"
  fg: "#f5f4f2"
  muted: "#aaa29a"
  border: "#39332e"
  rule: "#2a2521"
  speaking: "#30d158"
  silence: "#57534e"
  holding: "#f59e0b"
  agent: "#38bdf8"
typography:
  display:
    fontFamily: "Archivo, 'Segoe UI', sans-serif"
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "16px"
    lineHeight: 1.65
  data:
    fontFamily: "'JetBrains Mono', Consolas, monospace"
rounded:
  figure: "14px"
  control: "4px"
  track: "2px"
---

# Design System: StutterTurn Site Extension

## Overview

**Creative North Star: "Broadcast console"**

[The call console design](demo-ui/DESIGN.md) remains the visual authority. This document records its extension into [the landing page](index.html) and [judge view](judges/index.html), implemented by [site.css](site.css) and [site.js](site.js). It does not redefine the console's components or event semantics.

The landing route uses **Persuade** mode: one hero hierarchy (mono eyebrow, full-width headline, a single dek, console-key actions), an animated conceptual caller/agent loop in the console's own timeline language, the pinned evidence promoted directly beneath the hero, and a three-channel comparison leading to the judge view. The judge route uses **Operate** mode: brief presentation guidance surrounds the existing console, with the replay handoff below it. Both retain the warm near-black canvas, warm-white typography, flat rules, and semantic state colors.

## Colors

Warm white supplies primary text and action fills. Muted text, panel tones, and quiet borders establish hierarchy without shadows. The site frontmatter records the actual shared values used in its stylesheet.

Green represents caller speech, neutral gray represents silence, amber represents holding, and cyan represents an agent reply. On the landing page these colors explain a labeled concept; within the console they accompany reported states and events. The console's overlap and error treatments remain defined by its own design authority.

## Typography

Archivo supplies the wordmark, headline, and section headings; system fonts carry body text; JetBrains Mono carries every data voice on the landing page — the eyebrow, loop timecode, ruler and lane labels, decision flags, state chips, evidence fact labels and values, channel numbers, and revisions. Both web fonts reuse the console's local Latin-subset WOFF2 assets and fallbacks, and both are preloaded.

The landing headline uses a tight line height (0.98) and a fluid desktop scale (clamp 64–96px) across the full shell width; the dek is a single Archivo paragraph beneath it. Body copy remains comfortably spaced; short instrumentation and provenance labels use smaller type. The judge title stays subordinate to the console's large state tally.

## Layout

The landing shell is centered and capped at 1440px. Desktop pairs the headline with introductory copy, then uses ruled two-column explanation and evidence sections. At 720px and below these become a single reading column; at 480px and below navigation sits beneath the wordmark. Narrow layouts retain side gutters rather than shrinking body text.

The judge view uses a wider shell and compact introductory content. Its same-origin iframe loads the existing console once. The host hides duplicate console branding and adjusts the frame height when its content changes; the connection status, controls, provenance, and ledger remain part of the console. The console retains its own stacking breakpoints and horizontal scrolling for timeline and ledger content. A direct full-console link provides an alternate route.

## Elevation & Depth

There are no shadows. Panel fills and single-pixel borders separate the conceptual figure, controls, and evidence rows. Warm-white focus outlines make keyboard location visible.

Motion is restrained and fully gated. The landing page owns two moments: the hero concept loop (a 7.5 s CSS cycle — a 6 s left-to-right reveal wipe, playhead, holding pulse, decision-flag pops, and a 1.5 s completed hold) and a single opacity/translate scroll reveal on section entries. JavaScript starts the loop only while the figure is in view and never under `prefers-reduced-motion`; without JavaScript or with reduced motion, the base styles are the completed final frame and sections stay visible. Console-key buttons keep the console's 140 ms background transition and add a 1px press offset.

## Shapes

The conceptual figure uses the console monitor's restrained rounded container. Actions have smaller corners; timeline bars are nearly square. Supporting prose uses open sections and rules rather than repeated cards.

## Components

- **Console keys:** actions reuse the console transport's materials — primary is warm-white fill on dark text, the quiet key is the raised tone with the console's #70665d border and hover/active fills. Minimum height 48px, 140ms background transition, 1px press offset, reduced motion respected.
- **Concept loop (signature):** caller and agent lanes in the console's timeline language — mono lane tags, a phase ruler with ticks, amber WAIT and warm-white COMPLETE decision flags, an amber holding label and bar that pulse while open, a cyan reply, a one-pixel playhead, a state chip row echoing the tally, and a mono loop timecode labeled CONCEPT LOOP. A visible ILLUSTRATIVE SEQUENCE chip and accessible description identify it as illustrative, with no recorded timing or audio; the caption keeps that wording verbatim. Reduced motion and no-JS render the completed final frame statically.
- **Evidence:** the pinned handoff sits in a console-panel card directly after the hero. Mono uppercase fact labels with semantic status dots (speaking green for facts recorded in the handoff, holding amber for pending items), mono values, per-row hairlines, the unreduced human-review caveat, and a console-key link to the pinned source.
- **Channels:** the three comparison steps run full width as numbered channels (01–03, mono numbers over ruled columns); the numbering reflects the real operating sequence.
- **Footer:** brand line, repository/benchmark/console links, the SEP-28k CC BY-NC attribution, and the provenance line that nobody imitates stuttering — the recordings are real and labeled.
- **Presenter guide:** native disclosure keeps instructions available without occupying the main operating area when closed.
- **Embedded console:** the same controls, backend adapter, event renderer, status notices, and keyboard behavior as the full console; the site adds no second run model or simulated playback.

## Do's and Don'ts

- Do preserve the console's fonts, state meanings, visible labels, focus treatment, and honest provenance.
- Do keep illustrative sequences distinct from backend reports and received audio distinct from verified playback.
- Do preserve the landing page's reading space while keeping judge guidance compact enough to support operating the console.
- Don't turn the concept tracks into measured charts, add decorative waveforms, or imply recorded timing from their proportions.
- Don't duplicate console logic or present synthetic previews as replay evidence.

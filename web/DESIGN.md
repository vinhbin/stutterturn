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

The landing route uses **Persuade** mode: a large headline, a conceptual caller/agent sequence, a short comparison explanation, and pinned evidence lead to the judge view. The judge route uses **Operate** mode: brief presentation guidance surrounds the existing console, with the replay handoff below it. Both retain the warm near-black canvas, warm-white typography, flat rules, and semantic state colors.

## Colors

Warm white supplies primary text and action fills. Muted text, panel tones, and quiet borders establish hierarchy without shadows. The site frontmatter records the actual shared values used in its stylesheet.

Green represents caller speech, neutral gray represents silence, amber represents holding, and cyan represents an agent reply. On the landing page these colors explain a labeled concept; within the console they accompany reported states and events. The console's overlap and error treatments remain defined by its own design authority.

## Typography

Archivo supplies the wordmark, headline, and section headings; system fonts carry body text; JetBrains Mono identifies revisions and console data. Both web fonts reuse the console's local Latin-subset WOFF2 assets and fallbacks.

The landing headline uses a tight line height (0.98) and a large desktop scale (64–96px), with explicit responsive sizes. Body copy remains comfortably spaced; short instrumentation and provenance labels use smaller type. The judge title stays subordinate to the console's large state tally.

## Layout

The landing shell is centered and capped at 1440px. Desktop pairs the headline with introductory copy, then uses ruled two-column explanation and evidence sections. At 720px and below these become a single reading column; at 480px and below navigation sits beneath the wordmark. Narrow layouts retain side gutters rather than shrinking body text.

The judge view uses a wider shell and compact introductory content. Its same-origin iframe loads the existing console once. The host hides duplicate console branding and adjusts the frame height when its content changes; the connection status, controls, provenance, and ledger remain part of the console. The console retains its own stacking breakpoints and horizontal scrolling for timeline and ledger content. A direct full-console link provides an alternate route.

## Elevation & Depth

There are no shadows. Panel fills and single-pixel borders separate the conceptual figure, controls, and evidence rows. Warm-white focus outlines make keyboard location visible.

## Shapes

The conceptual figure uses the console monitor's restrained rounded container. Actions have smaller corners; timeline bars are nearly square. Supporting prose uses open sections and rules rather than repeated cards.

## Components

- **Primary action:** warm-white fill, dark text, a labeled destination, and a directional arrow. Its minimum height is 48px; the background transition lasts 140ms and respects reduced motion.
- **Concept sequence:** aligned caller and agent tracks explain speaking, a pause, continued speech, holding, and a reply. A visible caption and accessible description identify it as illustrative, with no recorded timing or audio. On phones the lane labels stack above their tracks and the pause label moves inside its segment.
- **Evidence:** definition lists and ruled observations separate recorded facts from limitations; mono revision text supports provenance. Links identify the pinned source.
- **Presenter guide:** native disclosure keeps instructions available without occupying the main operating area when closed.
- **Embedded console:** the same controls, backend adapter, event renderer, status notices, and keyboard behavior as the full console; the site adds no second run model or simulated playback.

## Do's and Don'ts

- Do preserve the console's fonts, state meanings, visible labels, focus treatment, and honest provenance.
- Do keep illustrative sequences distinct from backend reports and received audio distinct from verified playback.
- Do preserve the landing page's reading space while keeping judge guidance compact enough to support operating the console.
- Don't turn the concept tracks into measured charts, add decorative waveforms, or imply recorded timing from their proportions.
- Don't duplicate console logic or present synthetic previews as replay evidence.

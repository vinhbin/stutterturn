# Embedding the run-log chart on the judges page

To be wired **after the evidence-refresh PR merges** (another lane owns
`web/judges/index.html` right now — this folder only prepares the embed).

## The snippet

Paste these three lines into `web/judges/index.html`:

```html
<link rel="stylesheet" href="../tiger/chart.css">
<div id="tiger-chart" data-snapshot="../tiger/snapshot.json"></div>
<script src="../tiger/chart.js" defer></script>
```

## Where

Directly **below the replay-handoff section** (`<section id="replay-evidence" …>…</section>`),
still inside `<main>`, before the footer. The `<link>` can instead join the other
stylesheet links in `<head>` if preferred; the div and script stay in place.

## Notes

- The block is fully self-contained (own scoped styles, own font-face
  declarations for the same local WOFF2 files the site already uses, no
  libraries). It does not read or alter site.css/site.js.
- `data-snapshot` is optional — chart.js falls back to `snapshot.json`
  beside its own script URL — but keeping it explicit is robust.
- If `snapshot.json` is missing, the block renders an instruction message,
  never placeholder data. While the snapshot is offline-generated, every
  figure shows "LOCAL SNAPSHOT — NOT YET SERVED FROM TIGERDATA"; after a
  real `ingest.py` + `snapshot.py` run against the TigerData service,
  regenerating the snapshot flips the label to "Served from TigerData
  queries" on its own.
- Check it locally with `python -m http.server --directory web` →
  `http://localhost:8000/judges/`; `http://localhost:8000/tiger/preview.html`
  shows the block alone (dev-only page, not a judge route).

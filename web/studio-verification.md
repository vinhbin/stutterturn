# Studio refresh verification — 2026-10-10

The landing page, judge wrapper, and existing console now use the selected cool charcoal/cyan studio system. This is a presentation and interaction change; `demo-ui/app.js`, `demo-ui/adapter.js`, and the backend are unchanged.

## Reproducible checks

Run from the repository root:

```sh
node web/demo-ui/dev/checks/adapter-checks.mjs
node web/demo-ui/dev/checks/browser-checks.mjs
node web/demo-ui/dev/checks/site-checks.mjs
node --check web/site.js
git diff --check
```

Results: **38 adapter + 20 console browser + 38 site checks = 96 passed**. Browser checks use development fixtures and the local mock only. The site suite blocks non-local requests and checks 360, 390, 1280, and 1440px layouts, native keyboard controls, pause/seek lifecycle, reduced motion, no-JavaScript content, iframe resizing, and mobile setup/ledger access. No uncaught browser errors were observed.

## Visual review

Two batched capture rounds covered landing, judge preview, and disconnected full console at 1440×1000 and 390×844. An independent review identified three fixes: mobile access to setup, readable ledger explanations and empty state, and diagram microtext. All three were scored **resolved**, with disposition **ship** for that fix list and no material fix regressions observed.

The static design detector also flagged logical-padding wrappers, semantic overlap stripes, and short provenance notices. Render inspection confirmed that the wrappers have spacing; the overlap hatching and notices preserve event meaning. Functional diagram text was raised to at least 11px and narrow diagrams retain size through horizontal scrolling.

## Evidence and limitations

- Public evidence links now pin corrected replay v2 at artifact commit `9805a06` (runs executed on `bcf50d1`), which supersedes the original replay with faulty model input.
- The landing sequence is an illustration, with explicit no-audio/no-recorded-timing labels. Its controls do not operate a backend.
- Console screenshots and browser checks used synthetic events. They establish UI behavior, not model efficacy, audible interruption performance, or actual speaker playback.
- The console still plays no audio. No Gemini or ElevenLabs requests were made for this refresh.
- Browser validation used Chromium. Container queries and same-origin CSS view transitions are progressive enhancements; other browser engines were not exercised in this pass.

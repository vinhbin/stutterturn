# Studio refresh verification — 2026-10-10

The landing page, guided `/judge/` evaluation, `/live/` workspace, and existing console now use the selected cool charcoal/cyan studio system. This change preserves `demo-ui/app.js`, `demo-ui/adapter.js`, and backend behavior. Separately merged teammate backend work remains intact.

## Reproducible checks

Run from the repository root:

```sh
node web/demo-ui/dev/checks/adapter-checks.mjs
node web/demo-ui/dev/checks/browser-checks.mjs
node web/demo-ui/dev/checks/site-checks.mjs
node --check web/site.js
node --check web/judges/redirect.js
git diff --check
```

Results: **38 adapter + 20 console browser + 48 site checks = 106 passed**. Browser checks use development fixtures and the local mock only. The site suite blocks non-local requests and checks 360, 390, 1280, and 1440px layouts, native keyboard controls, pause/seek lifecycle, reduced motion, no-JavaScript content, iframe resizing, and mobile setup/ledger access. It also checks distinct judge/live roles, navigation, recorded evidence disclosures, and legacy `/judges/` redirect query/fragment preservation with a no-JavaScript fallback. No uncaught browser errors, external page requests, or automatic backend connections were observed.

## Visual review

Two batched capture rounds covered landing, judge preview, and disconnected full console at 1440×1000 and 390×844. An independent review identified three fixes: mobile access to setup, readable ledger explanations and empty state, and diagram microtext. All three were scored **resolved**, with disposition **ship** for that fix list and no material fix regressions observed.

The static design detector also flagged logical-padding wrappers, semantic overlap stripes, and short provenance notices. Render inspection confirmed that the wrappers have spacing; the overlap hatching and notices preserve event meaning. Functional diagram text was raised to at least 11px and narrow diagrams retain size through horizontal scrolling.

After the user approved the visual system and requested separate page roles, a further batch of eight captures covered the new judge guide and live workspace at both sizes, with full-page and viewport views. A fresh independent reviewer inspected all eight and the route code: **ship**, no material usability, responsive, navigation, or truth issues. These captures used an explicitly selected synthetic preview; page load itself starts no run.

## Evidence and limitations

- Public evidence links now pin corrected replay v2 at artifact commit `9805a06` (runs executed on `bcf50d1`), which supersedes the original replay with faulty model input.
- The landing sequence is an illustration, with explicit no-audio/no-recorded-timing labels. Its controls do not operate a backend.
- Console screenshots and browser checks used synthetic events. They establish UI behavior, not model efficacy, audible interruption performance, or actual speaker playback.
- The console still plays no audio. No Gemini or ElevenLabs requests were made for this refresh.
- Browser validation used Chromium. Container queries and same-origin CSS view transitions are progressive enhancements; other browser engines were not exercised in this pass.

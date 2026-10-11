# Hosted automatic connection — October 11, 2026

Console revision `bccef4bf7bb6` is deployed. The backend remains at
`667460f45fdd`; no provider keys, models, or service settings changed.

The hosted console connects on load, hides the URL/manual controls in Advanced
settings, and shows Retry connection on failure. Discovery allows 15 seconds.
HTTP401 explains how to sign in again. After an intentional Stop/Reset, the UI
explains that Start reconnects automatically. Opening the page does not start a
paid replay or play audio.

`native-auth-discovery.json` records a fresh Chromium context with credentials
supplied only for page sign-in (not API requests). Discovery returned HTTP200 for
health/configurations/sources without clicking Connect; two recordings and four
configuration choices were enabled. The candidate could be selected and the URL
was hidden. The screenshot captures that state.

`browser-audio-check.json` and JSONL logs record complete stock FP32 and candidate
runs from the automatically connected page. Both rendered nonzero source and
generated-speech audio. Stop during a generated reply and Reset after restarting
a source produced zero pending nodes and zero digital output. No page errors.

Local checks: four hosted connection scenarios (healthy, HTTP503, HTTP401, dropped
socket), 38 adapter, 20 console, 52 site and eight audio lifecycle checks passed;
synthetic Chromium audio rendering passed. The user's original connection failure
was not reproduced during diagnosis; the service and fresh native-auth discovery
were healthy. After deployment, the user explicitly confirmed “works now” and
“i can hear too.” This confirms their connection and hearing playback, without
establishing acoustic latency or natural barge-in performance.

Previous UI backup: `/opt/stutterturn/backups/bccef4bf7bb6/demo-ui/`.

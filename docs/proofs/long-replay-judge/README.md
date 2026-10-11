# Longer replay judge guide verification — October 11, 2026

Deployed static revision: `5175dcdb807a`. Backend remains `667460f45fdd`.
URL: https://64-177-51-1.sslip.io/judge/#long-replay

## Data

The two complete run logs in
[`agent/evidence/2026-10-11-long-replay`](../../../agent/evidence/2026-10-11-long-replay/README.md)
were committed at `21acc2c` before ingest. Real Tiger Data ingestion reported
22 runs / 353 events, including 10 superseded runs / 152 superseded events.
The pair adds 51 events. `comparison.py` queried Tiger Data and verified every
exported field against the source logs before writing `comparison.json`.
The original historical `snapshot.json` was not changed.

The primary figure shows X1 holding at 1.664 s where stock completes, and
stock's reported 0.200 s overlap. Both later cancellations and the stock
Gemini timeout remain present. Settings expose the equal silence gate and
different model/threshold. No general improvement or acoustic timing claim.

## Verification

- Four Python evidence tests pass: exact selected runs, metadata mismatch
  rejection, unchanged five-clip scope, and SQL-export equivalence to logs.
- Seven intercepted-browser scenarios pass: desktop, mobile, unavailable
  snapshot, missing provenance, both replay presets, and invalid preset input.
- Existing site checks: 52/52; console browser checks: 20/20; hosted connection
  scenarios: healthy, unavailable, authentication, dropped connection all pass.
- Deployed assets match the committed versions (normalizing line endings).
- Anonymous desktop (1440 px) and mobile (390 px) landing/judge loads have no
  script errors, failed resources or page overflow. Screenshots are included.
- Both authenticated live presets select the longer source and correct model,
  enable Start, and send zero run commands on page load. No paid runs were
  started by this verification. Source/reply audio transport is unchanged;
  this check does not claim new human listening or acoustic measurement.
- Anonymous `/live/`, `/demo-ui/app.js` and `/v0/health` continue to return 401.
- Authenticated backend health reports services on and `pcm16-v1` browser audio.

Details: [`verification.json`](verification.json). The exported database snapshot
is saved evidence; new cloud runs are still ingested explicitly. Listening
buttons start fresh runs after the visitor clicks Start, not playback of PCM
from the saved logs.

Deployment backed up replaced static files under
`/opt/stutterturn/backups/5175dcdb807a/previous`. No service restart, Caddy change,
provider-setting change, or database credential transfer was needed.

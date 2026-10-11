# Current working judge comparisons - October 11, 2026

Static revision: `7bdb1fc785f4`. Backend: `ed3d3ec93ce7`.
URL: https://64-177-51-1.sslip.io/judge/#long-replay

The main figure uses the working 10.4 s Stock FP32/X1 pair from
`agent/evidence/2026-10-11-long-replay-working`. Stock reports 0.050 s overlap;
X1 reports none. Both produced browser speech with no provider errors/timeouts.
The five-recording figure now includes both models on every source (10 runs),
with listening presets. All displayed runs rendered source and generated
speech in Chromium. The original Stock INT8/Patient summary remains secondary.

Tiger Data holds 37 runs / 631 events, including 10 superseded runs / 152
superseded events and all retained earlier provider attempts. The two displayed
query exports match their original saved logs. The historical snapshot and
previous longer-pair export remain available; no raw log was modified.

Validation:
- 47 backend tests passed locally and on Vultr.
- Six Python evidence checks passed, including both current datasets, fixed
  historical scope and the retained earlier failure.
- Seven comparison-browser scenarios passed; existing site checks 52/52 and
  console checks 20/20 passed. Hosted connection scenarios also passed.
- Deployed assets match their committed versions after line-ending normalization.
- Public desktop/mobile pages have no errors, failed resources or page overflow.
- Both longer replay presets connect and select the correct model/source;
  page loading sends no run command. Authenticated controls remain protected.
- Twelve selected replay runs have nonzero source/reply digital audio and no
  provider failures. Earlier failed attempts are documented in the proof packets.

`verification.json` records deployed asset and browser checks. Screenshots
cover both current figures at 1440 and 390 pixels. Provider/audio verification
is in `../gemini-empty-recovery/` and `../five-model-replays/`. This does not
measure acoustic timing or establish model efficacy or service reliability.

Replaced static files were backed up under
`/opt/stutterturn/backups/7bdb1fc785f4/previous`. Backend rollback material is
under `/opt/stutterturn/backups/ed3d3ec93ce7`. Keys stayed server-side; Tiger
credentials remained local and did not move to the VPS or browser.

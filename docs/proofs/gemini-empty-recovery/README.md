# Working longer pair after empty-reply handling correction

Backend `700d34762c1b`. Both saved replays completed with nonzero source/reply
digital audio in Chromium and no timeouts or provider errors. These two runs
did not require an empty-reply retry; retry recovery and exhaustion were
verified with controlled backend tests. Audio proof is digital, not acoustic.

The previous stock log had `timeout` plus `detail: empty reply`; that was an
incorrect classification. It is retained in the previous evidence packet.
The corrected backend distinguishes empty/provider errors from real deadlines,
retries empty non-blocked responses at most once, and respects Stop/resumption.

Subsequent five-clip checks exposed two real 10 s deadline expirations.
`ed3d3ec93ce7` raises the bounded Gemini deadline to 20 s and end-of-run
draining to 30 s. All 47 backend tests passed on Windows and Vultr. The two
last source pairs then completed with generated browser speech; see the
five-model packet. This does not establish provider reliability.

Reproduce a pair (paid API calls):
```sh
python web/demo-ui/dev/checks/audio-browser-check.py --access-file PRIVATE_JSON --out OUTPUT_DIR --source demo-long-WomenWhoStutter_19_1238s.wav --replay-only
```

Provider finish/block field reference: https://ai.google.dev/api/generate-content
No finish reason was recorded for the original empty response, so its provider
cause remains unknown. The extra retry output budget is a recovery allowance,
not a claim that token exhaustion caused that original failure.

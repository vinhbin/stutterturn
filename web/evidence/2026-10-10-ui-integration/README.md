# Model-only UI integration — October 10, 2026

These four JSONL files were retrieved from Guttuu's local server at commit
`3ed3786` after browser-driven runs through the LiveAdapter. The manifest lists
source, configuration, parameters, model hash, summaries and filenames.

```sh
python agent/server.py --services off --port 8765
```

Stock and patient completed on the same `HeStutters_4_32.wav` source. The stopped
run checks cancellation of the session; the restarted run checks fresh identity
after Stop and Reset. The source audio and model weights are not included.

The server ran Silero VAD and Smart Turn locally. Gemini and ElevenLabs were off,
so no response audio was generated or played. Null audio fields remain unknown;
reported `audible_interruption: false` is not a listening result. Decision times
are source-frame timestamps, not measured inference completion or response delay.

These files establish interface behavior and attribution only. They do not
validate human labels, candidate quality or speech outcomes. Guttuu's earlier
ten services-on traces are separate evidence linked from the site.

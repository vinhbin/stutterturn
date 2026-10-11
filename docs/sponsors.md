# Sponsor prizes and how we use them

Prize descriptions rechecked October 11 at [MLH](https://www.mlh.com/events/hacklanta-db/prizes). Actual integration status below supersedes the earlier planned uses. Evidence: [backend deployment](proofs/vultr-backend/README.md) and [browser audio](proofs/vultr-browser-audio/README.md).

## What we're entering

| Prize | Reward | Our use (load-bearing or honest-minor) | Get started |
|---|---|---|---|
| **Best Use of ElevenLabs** | Wireless earbuds | Streaming speech in the provider-enabled replay agent. Real generated speech now streams from Vultr into Web Audio, with source/reply playback, volume, Stop/Reset, and generation cancellation. Chromium digital rendering verified; acoustic timing is not measured. | mlh.link/elevenlabs |
| **Best Use of Vultr** | M5Stack Official Tab5 | Hosts the HTTPS site and runs ONNX inference, Gemini/ElevenLabs calls, and the authenticated HTTP/WebSocket backend. Real cloud runs and source/reply audio rendering verified in Chromium. No cloud training claim. | mlh.link/vultr |
| **Best Use of Gemini API** | MLH swag | Receives captured audio and generates replies with a dedicated response policy, including verified requests from Vultr. Gemini Live rival benchmarking remains unrun. | mlh.link/gemini |
| **Best Use of Tiger Data** | Stream Deck Mini | Run events stored in a TimescaleDB hypertable and queried through SQL views; the judge chart displays a saved database-query snapshot. Both current charts compare Stock FP32 with our X1 model: a working longer pair and five additional pairs. Database: 37 runs / 631 events, including retained failed attempts; exports verified against original logs. Historical Stock/Patient evidence remains secondary. | mlh.link/tigerdata |
| **DEV Writing Challenge** | $100 | Post-event: publish the benchmark story on dev.to/mlh-hackathon (selections monthly: technical substance, originality, storytelling) | dev.to/mlh-hackathon |

Main entry: **AI/ML track** (the progsu main-track rubric is still not in hand — Phase 0 task).

Our corpus note: no observed team won two MLH prizes at once — go deep on ElevenLabs + Vultr as the primary pair; Gemini/Tiger are real but secondary.

## Not entering, on purpose

- **Auth0** — no accounts in this product.
- **Solana** — no natural job; forcing it would be a sticker.
- **GoDaddy** (code MLHHL2694 if we change our minds) — a domain for the benchmark page is cheap but not load-bearing; decide at Phase 4 if time is spare.

## Other resources from the deck

- GitHub: mlh.link/hacklanta-github, Student Pack at mlh.link/pack.
- Everything: mlh.link/hacklanta.
- "I Demoed" stickers Sunday; MLH code of conduct: incidents@mlh.io, +1 (409) 202-6060.

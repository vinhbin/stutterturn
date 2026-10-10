# StutterTurn

StutterTurn is an engineering prototype for inspecting voice-agent turn taking on recorded speech. It helps presenters and judges compare a stock silence gate with a patient gate on the same recording and inspect decisions separately from reported response audio.

The landing page explains the mechanism. The judge guide at `/judge/` explains the hypothesis, evaluation steps, evidence, and limitations; it links to the separate operational workspace at `/live/`. The console discovers sources and configurations from a backend, starts fresh runs, displays caller/agent events on a shared timeline, and retains the run record and provenance. Development previews are synthetic, labeled, and never evidence. The browser plays no audio; receipt at the backend does not verify speaker playback. Candidate availability is backend supplied. No effectiveness claim is established by the interface.

## Confirmed visual direction

On 2026-10-10 the user selected a dark studio console: cool charcoal, cyan, stronger controls. They requested contemporary, usable layouts and technology, and rejected the prior warm brown/cream appearance as too reminiscent of Claude. Preserve the real operating controls, keyboard access, provenance, and mobile usability. The visual refresh is authorized across landing, judge view, and console.

The user approved the refreshed visual design and requested separate judge and live-demo pages. The judge page is an evaluator's guide, not a second operating console. The full console remains at `/demo-ui/`; `/judges/` is a compatibility route to `/judge/`.

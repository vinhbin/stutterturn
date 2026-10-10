# Reply-policy smoke check — October 10, 2026

Guttuu [reported two replies](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836)
that described the caller's speech as starting or cutting off. The revised
policy explicitly excludes unsolicited speech/recording commentary, asks for
a neutral fallback when intent is unclear, and is supplied through Gemini's
system instruction field. Caller audio remains user content.

[results.json](results.json) records six Gemini calls using
`gemini-3.8-flash`. The tested checkout was `7865b1d-dirty` with the prompt and
request-routing changes in this PR; it was not a clean committed revision.
The report pins the prompt and source SHA-256 hashes. No audio is redistributed.

## Method and observations

An unplayed stock replay of `HeStutters_4_32.wav`, with services off, captured
the two audio inputs at `_start_reply`. The capture wrapper still called the
original method. Source playback and TTS were disabled. Each captured input
was then passed twice to the actual `Services.reply_text` implementation.

| Input | Decision time | Samples | Calls | Observed reply |
|---|---:|---:|---:|---|
| Captured turn 1 | 1.120 s | 17,408 | 2 | What would you like help with? |
| Captured turn 2 | 4.992 s | 58,880 | 2 | What would you like help with? |

These are engine input slices, including any trailing synthetic silence;
the source recording itself is three seconds long. Gemini durations were
1.406–1.868 seconds. The four observed audio replies contained no speech
commentary. They do not prove that every slice lacked understandable meaning
or that the assistant's fallback was semantically optimal.

Two separate **text-only** probes used the same system policy and generation
settings. "What is two plus two?" received "Two plus two equals four." An
explicit microphone-clarity question received relevant microphone advice.
These check that the policy permits useful direct replies and requested audio
advice; they do not test audio recognition of those requests.

The offline request-routing regression and existing playback/lifecycle suite
passed **27 tests**:

```powershell
agent\.venv\Scripts\python.exe -m unittest discover -s agent/tests -v
```

## Limits and next acceptance

- Six provider calls, zero ElevenLabs calls, no speaker playback. This is not
  an audible end-to-end replay or acoustic cancellation test.
- One source, two engine input slices, two repetitions each. Responses are
  nondeterministic; this is observed behavior, not universal prompt compliance.
- Guttuu's two failing reply rows did not explicitly identify their source
  clips. This source appeared in his nearby playback smoke; exact reproduction
  of both failures is not established.
- No training, development-model selection or reserved-test evaluation was
  performed. This packet is outside `agent/evidence/` so Tiger ingestion does
  not treat it as a stock/patient comparison.
- Guttuu still needs to accept the revised replies during a real audible demo
  rehearsal, including clear requests. The neutral fallback alone does not
  establish a useful conversation.

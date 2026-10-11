# Retained attempts before the provider deadline correction

All three are HeStutters_5_123 on backend `700d34762c1b`:

- `20261011T061354Z-stock_fp32-e99d`: completed with generated speech.
- `20261011T061403Z-candidate-fc08`: actual 10 s Gemini request timeout.
- `20261011T061556Z-stock_fp32-f9f4`: actual 10 s Gemini request timeout.

The second and third produced no agent audio. A direct diagnostic request for
the candidate's source plus fallback silence completed in 9.671 s, near the
10 s cutoff. No underlying provider cause (quota, network, generation latency)
was established. The request deadline was raised to 20 s, with 30 s run-end
draining; Stop/resumption still cancel the request immediately. The subsequent
matched pair completed with generated browser speech for both configurations.
All these logs remain in Tiger Data, outside the selected working-demo packet.

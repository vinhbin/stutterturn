"""Export the ten matched, current Stock FP32/X1 runs from Tiger Data."""
import json
from pathlib import Path
import ingest
import snapshot

HERE = Path(__file__).resolve().parent
SCOPE = {'agent/evidence/2026-10-11-model-five-replay'}
OUT = HERE / 'model-five.json'


def main():
    url = ingest.connection_url()
    if not url:
        raise SystemExit('Tiger Data connection required')
    rows, meta = snapshot.rows_live(url, SCOPE)
    reference, reference_meta = snapshot.rows_offline(SCOPE)
    if sorted(rows, key=lambda r: r['run_id']) != sorted(reference, key=lambda r: r['run_id']) or meta != reference_meta:
        raise ValueError('Database values differ from saved logs')
    if len(rows) != 10 or meta['clips'] != 5 or meta['configs'] != ['candidate', 'stock_fp32']:
        raise ValueError('Expected exactly five matched Stock FP32/X1 pairs')
    for source in {r['source_id'] for r in rows}:
        if sorted(r['config'] for r in rows if r['source_id'] == source) != ['candidate', 'stock_fp32']:
            raise ValueError('Missing or duplicate configuration for ' + source)
    result = snapshot.assemble(rows, meta, offline=False)
    result['comparison_label'] = 'Stock FP32 vs our X1 model'
    result['caveats'] = [
        'Five 3-second excerpts from one show, one run per configuration. Per-recording observations, not general interruption rates.',
        'Both use a 0.2 s silence gate. Stock FP32 uses threshold 0.5; our X1 candidate uses 0.6. This compares configurations, not weights alone.',
        'The source is followed by 5 s synthetic silence. These excerpts do not establish completed-turn response delay.',
        'Browser source and reply audio rendered in verification. Times are server schedules, not measured acoustic playback.',
        'Each model pair shares a backend revision. The last two pairs use a 20 s Gemini deadline; earlier pairs use 10 s. Revisions are listed above. Failed earlier service attempts remain in the evidence archive.',
        'X1 is exploratory and unpromoted. No human-reviewed efficacy conclusion follows from these runs.'
    ]
    result['run_metadata'] = []
    for item in ingest.collect():
        if item['run']['evidence_dir'] in SCOPE:
            r = item['run']
            summary = json.loads(r['summary'])
            if r['reason'] != 'completed' or summary['timeouts'] or summary.get('errors'):
                raise ValueError('Run did not finish cleanly: ' + r['run_id'])
            result['run_metadata'].append({k: r[k] for k in ('run_id', 'commit_sha', 'model', 'model_sha256')})
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Exported five matched model pairs from Tiger Data; values match original logs.')


if __name__ == '__main__':
    main()

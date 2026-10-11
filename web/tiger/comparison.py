"""Export the exact long-replay pair from Tiger Data, verified against saved logs.

No offline publishing mode. Database export must equal the original JSONLs.
Credentials use ingest.connection_url(); see README.md.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import ingest

HERE = Path(__file__).resolve().parent
OUT = HERE / 'comparison.json'
SQL = HERE / 'comparison.sql'
PACKET = ingest.EVIDENCE_ROOT / '2026-10-11-long-replay'
RUN_IDS = ['20261011T053423Z-stock_fp32-bbcf', '20261011T053442Z-candidate-efd3']
NAMES = {'speech_start', 'speech_stop', 'turn_complete', 'turn_incomplete',
         'speaker_resumed', 'agent_audio_start', 'agent_audio_end', 'cancelled', 'timeout'}
EVENT_KEYS = ('seq', 't', 'name', 'prob', 'threshold', 'before_audible', 'service', 'overlap_s', 'timing')
RUN_KEYS = ('run_id', 'config', 'source_id', 'source_duration_s', 'commit_sha',
            'model', 'model_sha256', 'reason')


def local_rows():
    """Independent reference for checking the SQL export, never a DB substitute."""
    rows = []
    for rid in RUN_IDS:
        item = ingest.parse_log(PACKET / (rid + '.jsonl'))
        run = item['run']
        raw = [json.loads(e['raw']) for e in item['events']]
        decisions = [e for e in raw if e.get('name') in ('turn_complete', 'turn_incomplete')]
        summary = json.loads(run['summary'])
        rows.append({**{key: run[key] for key in RUN_KEYS},
                     'params': json.loads(run['params']),
                     'reported_overlap_s': summary['overlap_s'],
                     'timeouts': summary['timeouts'],
                     'first_decision_t': decisions[0]['t'],
                     'first_decision_name': decisions[0]['name'],
                     'events': [{key: e.get(key) for key in EVENT_KEYS}
                                for e in raw if e.get('name') in NAMES]})
    return rows


def validate(rows):
    if [r['run_id'] for r in rows] != RUN_IDS:
        raise ValueError('Expected exactly the two pinned runs in stock/candidate order')
    for field in ('source_id', 'source_duration_s', 'commit_sha'):
        if rows[0][field] != rows[1][field]:
            raise ValueError('Pair mismatch: ' + field)
    if [r['config'] for r in rows] != ['stock_fp32', 'candidate']:
        raise ValueError('Unexpected configurations')
    if any(r['reason'] != 'completed' for r in rows):
        raise ValueError('Incomplete run')
    settings = [{k: v for k, v in r['params'].items() if k != 'threshold'} for r in rows]
    if settings[0] != settings[1]:
        raise ValueError('Non-threshold settings differ')


def main():
    import psycopg
    from psycopg.rows import dict_row

    url = ingest.connection_url()
    if not url:
        raise SystemExit('Configure TIGER_SERVICE_URL or ~/.tiger_conn before exporting.')
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=15) as conn:
        rows = conn.execute(SQL.read_text(encoding='utf-8'), (RUN_IDS,)).fetchall()
    validate(rows)
    if rows != local_rows():
        raise ValueError('Tiger rows differ from the original logs; refusing to publish')
    result = {
        'schema_version': 1,
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'offline_fallback': False,
        'source_note': 'Saved Tiger Data query over two pinned Vultr runs; not live database status.',
        'query_sha256': hashlib.sha256(SQL.read_bytes()).hexdigest(),
        'log_sha256': {rid: hashlib.sha256((PACKET / (rid + '.jsonl')).read_bytes()).hexdigest() for rid in RUN_IDS},
        'runs': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Exported two Tiger Data runs; all selected fields match the saved JSONLs.')


if __name__ == '__main__':
    main()

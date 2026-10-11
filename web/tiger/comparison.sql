-- Exact hosted replay pair: source identity, settings, first decision and full
-- relevant timeline. No aggregation across speakers or model-efficacy estimate.
SELECT r.run_id, r.config, r.source_id, r.source_duration_s,
       r.commit_sha, r.model, r.model_sha256, r.params, r.reason,
       (r.summary->>'overlap_s')::double precision AS reported_overlap_s,
       r.summary->'timeouts' AS timeouts,
       (SELECT e.t FROM events e WHERE e.run_id = r.run_id
        AND e.name IN ('turn_complete', 'turn_incomplete')
        ORDER BY e.seq LIMIT 1) AS first_decision_t,
       (SELECT e.name FROM events e WHERE e.run_id = r.run_id
        AND e.name IN ('turn_complete', 'turn_incomplete')
        ORDER BY e.seq LIMIT 1) AS first_decision_name,
       (SELECT jsonb_agg(jsonb_build_object(
          'seq', e.seq, 't', e.t, 'name', e.name,
          'prob', e.prob, 'threshold', e.threshold,
          'before_audible', e.before_audible,
          'service', e.raw->'service', 'overlap_s', e.raw->'overlap_s',
          'timing', e.raw->'timing') ORDER BY e.seq)
        FROM events e WHERE e.run_id = r.run_id AND e.name IN (
          'speech_start', 'speech_stop', 'turn_complete', 'turn_incomplete',
          'speaker_resumed', 'agent_audio_start', 'agent_audio_end',
          'cancelled', 'timeout')) AS events
FROM runs r
WHERE r.run_id = ANY(%s) AND NOT r.superseded
ORDER BY CASE r.config WHEN 'stock_fp32' THEN 0 ELSE 1 END;

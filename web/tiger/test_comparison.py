"""Evidence invariants for the selected hosted comparison; no provider calls."""
import copy
import json
import unittest

import comparison
import ingest
import snapshot


class ComparisonTests(unittest.TestCase):
    def test_selected_logs_keep_hold_and_failure(self):
        rows = comparison.local_rows()
        comparison.validate(rows)
        stock, candidate = rows
        self.assertEqual(stock['first_decision_t'], 1.664)
        self.assertEqual(candidate['first_decision_name'], 'turn_incomplete')
        self.assertEqual(stock['reported_overlap_s'], 0.2)
        self.assertIsNone(candidate['reported_overlap_s'])
        self.assertEqual(stock['timeouts'], ['gemini'])
        for row in rows:
            self.assertTrue(any(e['name'] == 'cancelled' and e['before_audible'] for e in row['events']))

    def test_incomplete_or_mismatched_pair_rejected(self):
        rows = comparison.local_rows()
        for bad in [rows[:1], rows + [rows[0]]]:
            with self.assertRaises(ValueError):
                comparison.validate(bad)
        bad = copy.deepcopy(rows)
        bad[1]['source_id'] = 'different.wav'
        with self.assertRaises(ValueError):
            comparison.validate(bad)

    def test_historical_packet_remains_five_clips(self):
        rows, meta = snapshot.rows_offline()
        self.assertEqual(meta['runs_current'], 10)
        self.assertEqual(meta['clips'], 5)
        self.assertEqual({r['config'] for r in rows}, {'stock', 'patient'})

    def test_saved_database_export_matches_original_logs(self):
        saved = json.loads(comparison.OUT.read_text(encoding='utf-8'))
        self.assertFalse(saved['offline_fallback'])
        self.assertEqual(saved['runs'], comparison.local_rows())


if __name__ == '__main__':
    unittest.main()

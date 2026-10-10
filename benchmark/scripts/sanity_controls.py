"""Positive/negative controls for the Smart Turn harness (results in RESULTS.md section 5).
Positive: fluent audio cut mid-speech (0.5s before end-of-speech) should be judged incomplete.
Negative: fluent audio at true end-of-speech + 0.4s silence should be judged complete."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from run_model_arm import predict, SR
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(BASE, 'data/fluent_eval.csv'))))
mid = n = 0
for r in rows[:50]:
    x, _ = sf.read(os.path.join(BASE, 'audio', r['file']), dtype='float32')
    cut = float(r['speech_end']) - 0.5
    if cut < 1.0: continue
    n += 1; mid += int(predict(x[:int(cut*SR)]) > 0.5)
print(f'POSITIVE CONTROL mid-speech: N={n}, complete={mid} ({100*mid/n:.0f}%)')
comp = n2 = 0
for r in [r for r in rows if float(r['trailing_sil']) >= 0.4][:50]:
    x, _ = sf.read(os.path.join(BASE, 'audio', r['file']), dtype='float32')
    n2 += 1; comp += int(predict(x[:int((float(r['speech_end'])+0.4)*SR)]) > 0.5)
print(f'NEGATIVE CONTROL true end+0.4s: N={n2}, complete={comp} ({100*comp/n2:.0f}%)')

"""Build immutable dev/test eval items v1 (spec: benchmark/specs/eval-items-v1.md).

  python benchmark/scripts/build_items.py                 # build benchmark/items/v1; refuse if it exists
  python benchmark/scripts/build_items.py --check         # re-verify output + split hashes
  python benchmark/scripts/build_items.py --out DIR --annotations DIR   # tests

Energy VAD is imported from build_eval_sets.py (analyze, find_first_gap, fluent_features).
"""
import argparse, csv, datetime, hashlib, json, os, subprocess, sys
from collections import Counter, defaultdict

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_eval_sets as bes  # noqa: E402

SPLITS_DIR = os.path.join(BASE, "splits", "v1")
AUDIO = os.path.join(BASE, "audio")
DEFAULT_OUT = os.path.join(BASE, "items", "v1")
DEFAULT_ANN = os.path.join(BASE, "annotations")
SR = 16000
VAD_STOP_S = 0.2
MIN_DUR_S = 2.9
MIN_PEAK = 1e-4
MIN_FLUENT_SPEECH_S = 0.5
MIN_TRAILING_S = 0.50
DEV_PINNED = ("3030592364bc", "80b340")
TEST_PINNED = ("fd558b91fb40", "32c2")
ITEM_FIELDS = ["item_id", "clip_key", "audio", "split", "group", "kind", "silence_start_s",
               "resume_s", "turn_end_s", "observe_until_s", "label_source"]
ANN_HEADER = ["sample_id", "source_id", "context_ref", "speaker_id", "category", "time_origin",
              "block_onset_s", "resumption_s", "turn_end_s", "reviewer", "reviewed_at",
              "uncertainty", "accepted"]
CATEGORIES = {  # token -> (group, kind)
    "unfinished_stutter_block": ("stuttered", "unfinished"),
    "unfinished_fluent_pause": ("fluent", "unfinished"),
    "completed_stuttered_turn": ("stuttered", "completed"),
    "completed_fluent_turn": ("fluent", "completed"),
}
TIME_ORIGINS = {"clip_start": "clip-relative", "source_audio_start": "clip-relative",
                "episode_start": "subtract start/16000 from the split CSV row"}
GAB = {"stuttered": "stu", "fluent": "flu"}
KAB = {"unfinished": "unf", "completed": "cmp"}
QUEUE_N = {"unf_stu": 20, "unf_flu": 20, "cmp_stu": 25, "cmp_flu": 25}
TRUE = {"true", "1", "yes", "y", "t"}
FALSE = {"false", "0", "no", "n", "f"}

LIMITS = [
    "3 s clips cut from longer episodes; the mirror has only the windows. 'Fluent' means fluent-labelled clips, not fluent speakers (many participants stutter).",
    "Unfinished stuttered: Block>=2 clip with energy gap then energy resume in the clip. The resume may be another speaker, so items are energy_vad until a human confirms.",
    "Unfinished fluent is weaker: a mid-clip pause in a fluent-labelled clip may follow a finished sentence and the resume may be another speaker. Energy only until reviewed.",
    "Completed turns are NOT provable from clips: end-of-window silence is not a turn end. Energy 'completed' items are end_of_window proxies in separate files and must never be reported as turn-end delay. Real completed items come only from human labels made with episode context.",
    "The 3.0 s fallback is censored: with <=3 s of audio it essentially never becomes observable.",
    "The PLAN +50 ms delay criterion is degenerate under the single schedule: every completed item the model decides gets delay_s = vad_stop_s (0.2 s) exactly, so the median difference between any two models is 0. The measurable completed-turn signal under single is the rate decided at the first check vs censored/fallback, compared paired between models. Under interval, delay varies but is censored at the trailing silence. Gate reports must state this; delay medians must not be presented as evidence.",
    "Making completed-turn delay measurable needs human labels: about 50 (preferably 100) confirmed completed turns per group in dev, each with >=0.5 s of post-end audio in the clip. Stuttered completed turns may come from any dev clip with stuttering labels. Turn ends are confirmed in episode context (episode URL + split start/stop).",
    "Per-show VAD threshold differences (MSL quietest frames ~ -84 dB vs SV ~ -59 dB) shift item yield by show.",
    "8 of 117 overlap block items also carry Interjection >= 2.",
    "NaturalPause >= 2 on 10 of 117 block and 16 of 52 fluent overlap items.",
    "Review queue n = 20 per bucket cannot detect a fluent regression (95% CI about +/-20 points).",
    "Human-labelled dev/test clips must never feed training; see annotated_dev_test_keys. Annotations arriving after a build mean a new version (items/v2); v1 is never edited.",
    "No model or threshold selection uses test.",
]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_splits():
    """Run build_splits --check, then pin dev/test hashes against the spec. Returns sha dict."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_splits.py"), "--check"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("REFUSING: build_splits.py --check failed:\n" + r.stdout + r.stderr)
    sh = {s: sha256_file(os.path.join(SPLITS_DIR, f"{s}.csv")) for s in ["train", "dev", "test"]}
    for s, (a, b) in [("dev", DEV_PINNED), ("test", TEST_PINNED)]:
        if not (sh[s].startswith(a) and sh[s].endswith(b)):
            sys.exit(f"REFUSING: {s}.csv sha256 {sh[s]} does not match spec ({a}...{b})")
    return sh, r.stdout.strip()


def load_episode_urls():
    urls = {}
    with open(os.path.join(BASE, "data", "SEP-28k_episodes.csv"), newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 5:
                continue
            row = [x.strip() for x in row]
            urls[(row[3], row[4])] = row[2]
    return urls


class Gate:
    """Audio gate with per-clip cache."""
    def __init__(self, empty):
        self.empty, self.cache = empty, {}

    def __call__(self, key):
        if key in self.cache:
            return self.cache[key]
        p = os.path.join(AUDIO, key + ".wav")
        res = (None, None)
        if key in self.empty:
            res = ("empty_on_mirror", None)
        elif not os.path.isfile(p):
            res = ("missing_file", None)
        else:
            try:
                info = sf.info(p)
                dur = info.frames / info.samplerate if info.samplerate else 0.0
                if info.samplerate != SR:
                    res = ("wrong_sample_rate", None)
                elif dur < MIN_DUR_S:
                    res = ("too_short", None)
                else:
                    x, _ = sf.read(p, dtype="float32")
                    if x.ndim > 1:
                        x = x.mean(axis=1)
                    if float(np.max(np.abs(x))) < MIN_PEAK:
                        res = ("silent", None)
                    else:
                        res = (None, len(x) / SR)
            except Exception:
                res = ("unreadable", None)
        self.cache[key] = res
        return res


def mk_item(split, key, group, kind, ss, resume, te, obs, ls):
    return {"item_id": f"{split}-{GAB[group]}-{KAB[kind]}-{key}", "clip_key": key,
            "audio": f"audio/{key}.wav", "split": split, "group": group, "kind": kind,
            "silence_start_s": None if ss is None else float(ss),
            "resume_s": None if resume is None else float(resume),
            "turn_end_s": None if te is None else float(te), "observe_until_s": float(obs), "label_source": ls}


def vad_params():
    return {"sr": bes.SR, "frame_s": 0.030, "hop_s": 0.010, "gap_min_s": bes.GAP_MIN_S,
            "abs_floor_db": bes.ABS_FLOOR_DB, "rel_db": bes.REL_DB,
            "min_pre_speech_s": bes.MIN_PRE_SPEECH_S, "resume_run_frames": bes.RESUME_RUN,
            "vad_stop_s": VAD_STOP_S, "min_fluent_speech_s": MIN_FLUENT_SPEECH_S,
            "min_trailing_s": MIN_TRAILING_S}


def prov_row(item, file, row, source, ft, extra=None, **kw):
    d = {"item_id": item["item_id"], "file": file, "source": source, "annotation_file": None,
         "sample_id": None, "reviewer": None, "vad_params": vad_params(),
         "gap_or_pause_dur_s": None, "trailing_sil_s": None if ft is None else round(ft["trailing"], 3),
         "total_speech_s": None if ft is None else round(ft["total_speech"], 3),
         "show": row["show"], "block_votes": int(row["block"]),
         "interjection_votes": int(row["interjection"]),
         "natural_pause_votes": int(row["natural_pause"]),
         "replaced_energy_item": False, "onset_disagreement": None}
    d.update(kw)
    return d


def energy_pass(split, rows, gate, T):
    """Returns main items, proxies, provenance dict (by (file,item_id)), ft cache, extra candidates."""
    main, eow, prov, fts, cand_stu_cmp = {}, {}, {}, {}, []
    for r in rows:
        cat, key = r["category"], r["clip_key"]
        if cat == "fluent":
            need = True
        elif cat == "block":
            need = True
        elif cat == "other_disfluent" and split == "dev":
            need = True  # only for dev review-queue completed_stuttered candidates
        else:
            continue
        reason, dur = gate(key)
        tk = f"{split}/{cat}"
        if reason:
            T[tk][reason] += 1
            continue
        path = os.path.join(AUDIO, key + ".wav")
        a = bes.analyze(path)
        ft = bes.fluent_features(a)
        fts[key] = ft
        if cat == "block":
            gs, rs, pre, why = bes.find_first_gap(a)
            if why != "ok":
                T[tk][why] += 1
            elif rs - gs <= VAD_STOP_S:
                T[tk]["gap_not_checkable"] += 1
            else:
                it = mk_item(split, key, "stuttered", "unfinished", round(float(gs), 3),
                             round(float(rs), 3), None, dur, "energy_vad")
                main[it["item_id"]] = it
                prov[("main", it["item_id"])] = prov_row(
                    it, "main", r, "energy_vad", ft, gap_or_pause_dur_s=round(float(rs - gs), 3))
                T[tk]["item_stuttered_unfinished"] += 1
        if cat in ("block", "other_disfluent") and split == "dev":
            if ft is not None and ft["trailing"] >= MIN_TRAILING_S:
                te = round(float(ft["speech_end"]), 3)
                if dur - te >= VAD_STOP_S:
                    cand_stu_cmp.append(mk_item(split, key, "stuttered", "completed", te, None, te,
                                                dur, "energy_vad"))
        if cat == "fluent":
            if ft is None or ft["total_speech"] < MIN_FLUENT_SPEECH_S:
                T[tk]["no_speech_detected"] += 1
                continue
            if not ft["pauses"]:
                T[tk]["unf_no_mid_pause"] += 1
            else:
                ps, pe = ft["pauses"][0]
                if pe - ps <= VAD_STOP_S:
                    T[tk]["gap_not_checkable"] += 1
                else:
                    it = mk_item(split, key, "fluent", "unfinished", ps, pe, None, dur, "energy_vad")
                    main[it["item_id"]] = it
                    prov[("main", it["item_id"])] = prov_row(
                        it, "main", r, "energy_vad", ft, gap_or_pause_dur_s=round(pe - ps, 3))
                    T[tk]["item_fluent_unfinished"] += 1
            if ft["trailing"] < MIN_TRAILING_S:
                T[tk]["cmp_trailing_lt_0.5"] += 1
            else:
                te = round(float(ft["speech_end"]), 3)
                if dur - te < VAD_STOP_S:
                    T[tk]["post_end_too_short"] += 1
                else:
                    it = mk_item(split, key, "fluent", "completed", te, None, te, dur, "energy_vad")
                    eow[it["item_id"]] = it
                    prov[("end_of_window", it["item_id"])] = prov_row(it, "end_of_window", r,
                                                                       "energy_vad_end_of_window", ft)
                    T[tk]["item_fluent_completed_proxy"] += 1
    return main, eow, prov, fts, cand_stu_cmp


def parse_bool(s):
    s = s.strip().lower()
    return True if s in TRUE else False if s in FALSE else None


def apply_annotations(ann_dir, rowmap, state, gate, urls_unused, T, ann_files, annotated_keys):
    """state[split] = {'main':{}, 'eow':{}, 'prov':{}, 'fts':{}}. Mutates. rowmap: key -> (split,row)."""
    outcomes = []
    if not os.path.isdir(ann_dir):
        return outcomes
    seen = set()
    for fn in sorted(os.listdir(ann_dir)):
        if not fn.endswith(".csv"):
            continue
        fp = os.path.join(ann_dir, fn)
        ann_files[fn] = sha256_file(fp)
        with open(fp, newline="", encoding="utf-8") as f:
            rd = csv.reader(f)
            hdr = [h.strip() for h in next(rd, [])]
            if hdr != ANN_HEADER:
                sys.exit(f"annotation file {fn}: header mismatch {hdr}")
            for raw in rd:
                if not raw or not any(x.strip() for x in raw):
                    continue
                d = dict(zip(hdr, [x.strip() for x in raw]))
                sid = d["sample_id"]
                key = d["source_id"][:-4] if d["source_id"].endswith(".wav") else d["source_id"]
                if key not in rowmap:
                    T["annotations/any"]["annotations_not_in_dev_test"] += 1
                    outcomes.append((fn, sid, "annotations_not_in_dev_test"))
                    continue
                split, srow = rowmap[key]
                tk = f"{split}/{srow['category']}"
                annotated_keys.add(key)

                def rej(reason):
                    T[tk][reason if reason == "uncertain" else "ann_" + reason] += 1
                    outcomes.append((fn, sid, reason))

                cat = d["category"]
                if cat not in CATEGORIES:
                    rej("bad_category"); continue
                group, kind = CATEGORIES[cat]
                acc = parse_bool(d["accepted"])
                st = state[split]
                iid = f"{split}-{GAB[group]}-{KAB[kind]}-{key}"
                if acc is False:
                    if not d["reviewer"]:
                        rej("declined_without_reviewer"); continue
                    removed = False
                    if kind == "unfinished":
                        removed = st["main"].pop(iid, None) is not None
                        st["prov"].pop(("main", iid), None)
                    elif group == "fluent":
                        removed = st["eow"].pop(iid, None) is not None
                        st["prov"].pop(("end_of_window", iid), None)
                    T[tk]["human_rejected"] += 1
                    outcomes.append((fn, sid, f"human_rejected(energy_item_removed={removed})"))
                    continue
                if acc is None:
                    rej("accepted_not_boolean"); continue
                if d["uncertainty"]:
                    rej("uncertain"); continue
                to = d["time_origin"]
                if to not in TIME_ORIGINS:
                    rej("bad_time_origin"); continue
                reason, dur = gate(key)
                if reason:
                    rej("audio_" + reason); continue
                off = 0.0 if to != "episode_start" else int(srow["start"]) / 16000
                try:
                    tv = {c: (float(d[c]) - off if d[c] else None)
                          for c in ["block_onset_s", "resumption_s", "turn_end_s"]}
                except ValueError:
                    rej("bad_time_value"); continue
                need = ["resumption_s"] if kind == "unfinished" else ["turn_end_s"]
                if any(tv[c] is None for c in need):
                    rej("missing_time"); continue
                if any(v is not None and not (0 <= v <= dur) for v in tv.values()):
                    rej("time_out_of_range"); continue
                if (key, kind, group) in seen:
                    rej("duplicate_annotation"); continue
                if kind == "unfinished":
                    old = st["main"].get(iid)
                    if old is not None:
                        ss, disagree = old["silence_start_s"], None
                        if tv["block_onset_s"] is not None:
                            disagree = abs(tv["block_onset_s"] - ss) > 0.10
                    elif tv["block_onset_s"] is not None:
                        ss, disagree = round(tv["block_onset_s"], 3), None
                    else:
                        rej("missing_time"); continue
                    rs = round(tv["resumption_s"], 3)
                    if rs - ss <= VAD_STOP_S:
                        rej("gap_not_checkable"); continue
                    it = mk_item(split, key, group, kind, ss, rs, None, dur, "human")
                    st["main"][iid] = it
                    ft = st["fts"].get(key)
                    p = prov_row(it, "main", srow, "human", ft, annotation_file=fn, sample_id=sid,
                                 reviewer=d["reviewer"], gap_or_pause_dur_s=round(rs - ss, 3),
                                 replaced_energy_item=old is not None, onset_disagreement=disagree)
                    st["prov"][("main", iid)] = p
                    T[tk]["ann_human_" + group + "_unfinished"] += 1
                    outcomes.append((fn, sid, f"human_unfinished_{'replacement' if old else 'new'}"
                                              f"(onset_disagreement={disagree})"))
                else:
                    te = round(tv["turn_end_s"], 3)
                    if dur - te < VAD_STOP_S:
                        rej("post_end_too_short"); continue
                    it = mk_item(split, key, group, kind, te, None, te, dur, "human")
                    st["main"][iid] = it
                    ft = st["fts"].get(key)
                    st["prov"][("main", iid)] = prov_row(it, "main", srow, "human", ft,
                                                         annotation_file=fn, sample_id=sid,
                                                         reviewer=d["reviewer"])
                    T[tk]["ann_human_" + group + "_completed"] += 1
                    outcomes.append((fn, sid, "human_completed_new"))
                seen.add((key, kind, group))
    return outcomes


def hkey(item_id):
    return hashlib.sha256(item_id.encode()).hexdigest()


def build_queue(dev_rows_by_key, energy_dev, urls):
    """energy_dev: dict bucket -> list of energy items (pre-annotation)."""
    qrows, side = [], []
    n = 0
    for bucket, cat in [("unf_stu", "unfinished_stutter_block"), ("unf_flu", "unfinished_fluent_pause"),
                        ("cmp_stu", "completed_stuttered_turn"), ("cmp_flu", "completed_fluent_turn")]:
        pool = sorted(energy_dev[bucket], key=lambda it: hkey(it["item_id"]))
        for it in pool[:QUEUE_N[bucket]]:
            n += 1
            sid = f"D{n:03d}"
            r = dev_rows_by_key[it["clip_key"]]
            url = urls.get((r["show"], r["ep_id"]), "")
            ref = f"{url}#t={format(int(r['start']) / 16000, '.3f').rstrip('0').rstrip('.')}"
            qrows.append({"sample_id": sid, "source_id": it["clip_key"], "context_ref": ref,
                          "speaker_id": "", "category": cat, "time_origin": "clip_start",
                          "block_onset_s": "", "resumption_s": "", "turn_end_s": "", "reviewer": "",
                          "reviewed_at": "", "uncertainty": "", "accepted": ""})
            side.append({"sample_id": sid, "item_id": it["item_id"], "clip_key": it["clip_key"],
                         "category": cat, "silence_start_s": it["silence_start_s"],
                         "resume_s": "" if it["resume_s"] is None else it["resume_s"],
                         "turn_end_s": "" if it["turn_end_s"] is None else it["turn_end_s"],
                         "observe_until_s": it["observe_until_s"]})
    return qrows, side


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_jsonl(path, items):
    with open(path, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")


def counts(items_by_split):
    c = Counter()
    for sp, items in items_by_split.items():
        for it in items:
            c[f"{sp}|{it['group']}|{it['kind']}|{it['label_source']}"] += 1
    return dict(sorted(c.items()))


def do_check(out):
    mp = os.path.join(out, "manifest.json")
    if not os.path.isfile(mp):
        sys.exit(f"no manifest at {mp}")
    m = json.load(open(mp))
    bad = []
    for s, h in m["split_sha256"].items():
        cur = sha256_file(os.path.join(SPLITS_DIR, f"{s}.csv"))
        if cur != h:
            bad.append(f"split {s}: {cur} != {h}")
    for fn, h in m["output_sha256"].items():
        p = os.path.join(out, fn)
        if not os.path.isfile(p):
            bad.append(f"missing {fn}")
        elif sha256_file(p) != h:
            bad.append(f"hash mismatch {fn}")
    if bad:
        print("CHECK FAILED:\n  " + "\n  ".join(bad))
        return 1
    print(f"OK: {out} verified ({len(m['output_sha256'])} outputs, {len(m['split_sha256'])} splits)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--annotations", default=DEFAULT_ANN)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    if args.check:
        sys.exit(do_check(out))
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} already exists (items are immutable; new annotations mean a new version)")
    split_sha, split_check = verify_splits()

    empty = set()
    ep = os.path.join(AUDIO, "empty_on_mirror.txt")
    if os.path.exists(ep):
        empty = {l.strip() for l in open(ep) if l.strip()}
    gate = Gate(empty)
    train_keys = {r["clip_key"] for r in read_csv(os.path.join(SPLITS_DIR, "train.csv"))}
    split_rows = {s: read_csv(os.path.join(SPLITS_DIR, f"{s}.csv")) for s in ["dev", "test"]}
    rowmap = {r["clip_key"]: (s, r) for s in split_rows for r in split_rows[s]}
    urls = load_episode_urls()
    T = defaultdict(Counter)

    state, energy_main, energy_eow, stu_cmp = {}, {}, {}, []
    for s in ["dev", "test"]:
        main, eow, prov, fts, cand = energy_pass(s, split_rows[s], gate, T)
        state[s] = {"main": main, "eow": eow, "prov": prov, "fts": fts}
        energy_main[s], energy_eow[s] = dict(main), dict(eow)
        if s == "dev":
            stu_cmp = cand
    # review-queue pools use energy items before any annotation
    pools = {"unf_stu": [i for i in energy_main["dev"].values() if i["group"] == "stuttered"],
             "unf_flu": [i for i in energy_main["dev"].values() if i["group"] == "fluent"],
             "cmp_stu": stu_cmp, "cmp_flu": list(energy_eow["dev"].values())}

    ann_files, annotated = {}, set()
    outcomes = apply_annotations(args.annotations, rowmap, state, gate, urls, T, ann_files, annotated)

    for s_ in ["dev", "test"]:  # leakage assertions, before anything is written
        for it in list(state[s_]["main"].values()) + list(state[s_]["eow"].values()):
            assert it["clip_key"] not in train_keys, it["item_id"]
            assert it["clip_key"] in rowmap and rowmap[it["clip_key"]][0] == s_, it["item_id"]

    os.makedirs(os.path.dirname(out), exist_ok=True)
    os.mkdir(out)
    files, final = {}, {}
    prov_all = []
    for s in ["dev", "test"]:
        st = state[s]
        mi = sorted(st["main"].values(), key=lambda i: i["item_id"])
        ei = sorted(st["eow"].values(), key=lambda i: i["item_id"])
        final[s] = (mi, ei)
        write_jsonl(os.path.join(out, f"{s}.jsonl"), mi)
        write_jsonl(os.path.join(out, f"{s}_end_of_window.jsonl"), ei)
        prov_all += list(st["prov"].values())
    prov_all.sort(key=lambda p: (p["item_id"], p["file"]))
    write_jsonl(os.path.join(out, "provenance.jsonl"), prov_all)
    dev_by_key = {r["clip_key"]: r for r in split_rows["dev"]}
    qrows, side = build_queue(dev_by_key, pools, urls)
    write_csv(os.path.join(out, "review_queue_dev.csv"), ANN_HEADER, qrows)
    write_csv(os.path.join(out, "review_queue_dev_energy.csv"),
              ["sample_id", "item_id", "clip_key", "category", "silence_start_s", "resume_s",
               "turn_end_s", "observe_until_s"], side)

    out_names = ["dev.jsonl", "test.jsonl", "dev_end_of_window.jsonl", "test_end_of_window.jsonl",
                 "provenance.jsonl", "review_queue_dev.csv", "review_queue_dev_energy.csv"]
    outsha = {n: sha256_file(os.path.join(out, n)) for n in out_names}
    main_counts = counts({s: final[s][0] for s in final})
    eow_counts = counts({s: final[s][1] for s in final})
    tallies = {k: dict(sorted(v.items())) for k, v in sorted(T.items())}
    manifest = {
        "version": "v1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "benchmark/scripts/build_items.py",
        "script_sha256": sha256_file(os.path.abspath(__file__)),
        "build_eval_sets_sha256": sha256_file(os.path.join(HERE, "build_eval_sets.py")),
        "split_sha256": split_sha, "split_check": split_check,
        "vad_params": vad_params(),
        "annotation_files": ann_files,
        "category_vocabulary": sorted(CATEGORIES),
        "time_origin_handling": TIME_ORIGINS,
        "tallies": tallies,
        "item_counts_main": main_counts, "item_counts_end_of_window": eow_counts,
        "review_queue": {"rows": len(qrows), "per_bucket": QUEUE_N,
                         "candidates_available": {k: len(v) for k, v in pools.items()},
                         "note": "n=20 per bucket cannot detect a fluent regression (95% CI about +/-20 points)"},
        "output_sha256": outsha,
        "annotated_dev_test_keys": sorted(annotated),
        "test_sealed": True,
        "limits": LIMITS,
    }
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)

    print("ITEM COUNTS (main):")
    for k, v in main_counts.items():
        print(f"  {k}: {v}")
    print("ITEM COUNTS (end_of_window proxies):")
    for k, v in eow_counts.items():
        print(f"  {k}: {v}")
    print("TALLIES:")
    for k, v in tallies.items():
        print(f"  {k}: {v}")
    print("REVIEW QUEUE:", len(qrows), "rows; candidates available:", {k: len(v) for k, v in pools.items()})
    if outcomes:
        print("ANNOTATION OUTCOMES:")
        for o in outcomes:
            print("  ", o)
    print("SHA256:")
    for n, h in outsha.items():
        print(f"  {n}: {h}")
    print(f"\nRECORD IN DECISION LOG: test.jsonl sha256 = {outsha['test.jsonl']} "
          f"(dev.jsonl = {outsha['dev.jsonl']}). Test is sealed; no model/threshold selection uses it.")


if __name__ == "__main__":
    main()

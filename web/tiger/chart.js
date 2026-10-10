/* StutterTurn — run-log time-series block (web/tiger/).
 * Self-contained, no libraries. Renders web/tiger/snapshot.json into
 * #tiger-chart: per-clip stock-vs-patient first-completion timelines and
 * per-run decision→first-audio gaps. Every figure shows the snapshot's
 * provenance line; an offline snapshot gets a visible LOCAL SNAPSHOT label.
 * Nothing is drawn that is not in the snapshot; fetch failure renders a
 * message, never placeholder data. Values are per clip — n=5, no rates. */
(function () {
  'use strict';
  var script = document.currentScript;

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function secs(v) { return v === null || v === undefined ? '—' : v.toFixed(3) + ' s'; }
  function pct(v, max) { return (100 * v / max).toFixed(3) + '%'; }

  function markTitle(kind, run, t) {
    return kind + ' at ' + secs(t) + ' — ' + run.config + ', run ' + run.run_id;
  }

  function mark(cls, t, tmax, title) {
    var m = el('span', 'tgr-mark ' + cls);
    m.style.left = pct(t, tmax);
    m.title = title;
    m.setAttribute('aria-hidden', 'true');
    return m;
  }

  function ruler(tmax, step) {
    var r = el('div', 'tgr-ruler');
    for (var t = 0; t <= tmax; t += step) {
      var s = el('span', null, t + ' s');
      s.style.left = pct(t, tmax);
      r.appendChild(s);
    }
    return r;
  }

  function legend() {
    var wrap = el('div', 'tgr-legend');
    [['tgr-mark-complete', 'complete — model decision'],
     ['tgr-mark-fallback', 'complete — 3.0 s silence fallback'],
     ['tgr-mark-cancel', 'reply cancelled before audio'],
     ['tgr-mark-audio', 'first agent audio (scheduled play)']
    ].forEach(function (item) {
      var s = el('span');
      s.appendChild(el('i', 'tgr-mark ' + item[0]));
      s.appendChild(document.createTextNode(item[1]));
      wrap.appendChild(s);
    });
    return wrap;
  }

  function provenance(snap) {
    var p = el('p', 'tgr-provenance');
    var strong = el('strong', null, snap.source_note);
    p.appendChild(strong);
    p.appendChild(document.createTextNode(
      ' · generated ' + snap.generated_utc +
      ' · agent commit ' + snap.evidence.commit +
      ' · contract v' + snap.evidence.contract +
      ' · ' + snap.evidence.runs_current + ' runs / ' + snap.evidence.clips + ' clips' +
      ' · ' + snap.evidence.runs_superseded_excluded + ' superseded runs excluded'));
    return p;
  }

  function offlineBadge() {
    return el('span', 'tgr-badge', 'Local snapshot — not yet served from TigerData');
  }

  function figureFooter(snap) {
    var f = el('div');
    if (snap.offline_fallback) f.appendChild(offlineBadge()).style.cssText = 'display:inline-block;margin-top:12px;';
    f.appendChild(provenance(snap)).style.marginTop = '10px';
    return f;
  }

  function valuesLine(run) {
    var v = el('p', 'tgr-values');
    function add(label, value, sep) {
      if (sep) v.appendChild(document.createTextNode(' → '));
      v.appendChild(document.createTextNode(label + ' '));
      v.appendChild(el('b', null, value));
    }
    var how = run.trigger === 'smart_turn'
      ? 'model' + (run.prob !== null && run.prob !== undefined ? ' p ' + run.prob.toFixed(2) : '')
      : '3.0 s fallback';
    add('complete', secs(run.first_complete_t) + ' (' + how + ')');
    if (run.cancelled_before_audio) add('cancelled before audio', secs(run.cancelled_t), true);
    if (run.answered_decision_t !== null && run.answered_decision_t !== run.first_complete_t) {
      add('answered complete', secs(run.answered_decision_t), true);
    }
    if (run.first_audio_t !== null && run.first_audio_t !== undefined) {
      add('audio', secs(run.first_audio_t), true);
    } else {
      v.appendChild(document.createTextNode(' → no agent audio'));
    }
    return v;
  }

  function lane(run, tmax) {
    var row = el('div', 'tgr-lane');
    row.appendChild(el('span', 'tgr-lane-tag', run.config));
    var track = el('div', 'tgr-track');
    track.style.setProperty('--tgr-ticks', String(tmax));
    if (run.source_duration_s) {
      var srcBand = el('span', 'tgr-src');
      srcBand.style.width = pct(run.source_duration_s, tmax);
      srcBand.title = 'Real recording plays 0–' + run.source_duration_s.toFixed(1) +
        ' s; the agent then hears 5 s of synthetic silence.';
      track.appendChild(srcBand);
    }
    if (run.first_complete_t !== null) {
      track.appendChild(mark(
        run.trigger === 'smart_turn' ? 'tgr-mark-complete' : 'tgr-mark-fallback',
        run.first_complete_t, tmax,
        markTitle('First completion decision (' + (run.trigger || 'unknown trigger') + ')', run, run.first_complete_t)));
    }
    if (run.cancelled_before_audio && run.cancelled_t !== null) {
      track.appendChild(mark('tgr-mark-cancel', run.cancelled_t, tmax,
        markTitle('Speaker resumed; pending reply cancelled before any audio', run, run.cancelled_t)));
    }
    if (run.answered_decision_t !== null && run.answered_decision_t !== run.first_complete_t) {
      track.appendChild(mark('tgr-mark-complete', run.answered_decision_t, tmax,
        markTitle('Completion decision the audio answered', run, run.answered_decision_t)));
    }
    if (run.first_audio_t !== null && run.first_audio_t !== undefined) {
      track.appendChild(mark('tgr-mark-audio', run.first_audio_t, tmax,
        markTitle('First agent audio scheduled to play', run, run.first_audio_t)));
    }
    row.appendChild(track);
    row.appendChild(valuesLine(run));
    return row;
  }

  var CONFIG_ORDER = ['stock', 'patient'];
  function orderedConfigs(clip) {
    return CONFIG_ORDER.filter(function (c) { return clip.configs[c]; })
      .concat(Object.keys(clip.configs).filter(function (c) { return CONFIG_ORDER.indexOf(c) < 0; }));
  }

  function timelineFigure(snap, tmax) {
    var fig = el('section', 'tgr-figure');
    fig.appendChild(el('h4', 'tgr-figtitle', 'First completion decision per clip — stock vs patient'));
    fig.appendChild(el('p', 'tgr-fignote',
      'When each configuration first decided the turn was complete on the same replayed recording, ' +
      'and what became of it. The shaded band is the real 3 s recording; after it, the agent hears synthetic silence.'));
    fig.appendChild(legend());
    fig.appendChild(ruler(tmax, 2));
    snap.clips.forEach(function (clip) {
      var group = el('div', 'tgr-clip');
      group.appendChild(el('h5', 'tgr-clip-name', clip.source_id));
      orderedConfigs(clip).forEach(function (cfg) {
        var run = clip.configs[cfg];
        run.config = run.config || cfg;
        group.appendChild(lane(run, tmax));
      });
      fig.appendChild(group);
    });
    fig.appendChild(figureFooter(snap));
    return fig;
  }

  function gapFigure(snap, gmax) {
    var fig = el('section', 'tgr-figure');
    fig.appendChild(el('h4', 'tgr-figtitle', 'Decision → first agent audio, per run'));
    fig.appendChild(el('p', 'tgr-fignote',
      'Time from the completion decision the audio actually answered to the first agent audio sample ' +
      'scheduled to play (Gemini + ElevenLabs latency included, reported beside each bar). ' +
      'Per-run values from 5 clips — not a latency benchmark.'));
    snap.clips.forEach(function (clip) {
      var group = el('div', 'tgr-clip');
      group.appendChild(el('h5', 'tgr-clip-name', clip.source_id));
      orderedConfigs(clip).forEach(function (cfg) {
        var run = clip.configs[cfg];
        var row = el('div', 'tgr-gap-row');
        row.appendChild(el('span', 'tgr-lane-tag', cfg));
        var bar = el('div', 'tgr-gap-bar');
        if (run.gap_s !== null && run.gap_s !== undefined) {
          var fill = el('span', 'tgr-gap-fill');
          fill.style.width = pct(run.gap_s, gmax);
          fill.title = markTitle('Decision → first audio gap of ' + secs(run.gap_s), run, run.answered_decision_t);
          bar.appendChild(fill);
        }
        row.appendChild(bar);
        var v = el('p', 'tgr-values');
        if (run.gap_s !== null && run.gap_s !== undefined) {
          v.appendChild(document.createTextNode('decision ' + secs(run.answered_decision_t) + ' → audio ' + secs(run.first_audio_t) + ' · gap '));
          v.appendChild(el('b', null, secs(run.gap_s)));
          v.appendChild(document.createTextNode(
            ' (LLM ' + secs(run.llm_latency_s) + ' · TTS first audio ' + secs(run.tts_first_audio_s) + ')'));
        } else {
          v.textContent = 'no agent audio in this run';
        }
        row.appendChild(v);
        group.appendChild(row);
      });
      fig.appendChild(group);
    });
    fig.appendChild(figureFooter(snap));
    return fig;
  }

  function caveats(snap) {
    var f = el('footer', 'tgr-caveats');
    f.appendChild(el('h4', 'tgr-figtitle', 'Read these before quoting a number'));
    var ul = el('ul');
    (snap.caveats || []).forEach(function (c) { ul.appendChild(el('li', null, c)); });
    f.appendChild(ul);
    return f;
  }

  function render(mount, snap) {
    var tmax = 1, gmax = 0.5;
    snap.clips.forEach(function (clip) {
      Object.keys(clip.configs).forEach(function (cfg) {
        var r = clip.configs[cfg];
        [r.first_complete_t, r.cancelled_t, r.answered_decision_t, r.first_audio_t].forEach(function (t) {
          if (t !== null && t !== undefined && t > tmax) tmax = t;
        });
        if (r.gap_s !== null && r.gap_s !== undefined && r.gap_s > gmax) gmax = r.gap_s;
      });
    });
    tmax = Math.ceil(tmax);
    gmax = Math.ceil(gmax * 2) / 2;

    var block = el('section', 'tgr-block');
    block.setAttribute('aria-label', 'Run-log time series: stock vs patient replay evidence');
    var head = el('header', 'tgr-head');
    head.appendChild(el('h3', 'tgr-title', 'Every run is a time series'));
    head.appendChild(snap.offline_fallback
      ? offlineBadge()
      : el('span', 'tgr-badge tgr-badge-live', 'Served from TigerData queries'));
    head.appendChild(provenance(snap));
    block.appendChild(head);
    block.appendChild(timelineFigure(snap, tmax));
    block.appendChild(gapFigure(snap, gmax));
    block.appendChild(caveats(snap));
    mount.textContent = '';
    mount.appendChild(block);
  }

  function showError(mount, msg) {
    mount.textContent = '';
    var block = el('section', 'tgr-block');
    block.appendChild(el('p', 'tgr-note tgr-error',
      'Run-log chart: could not load snapshot.json (' + msg + '). ' +
      'Generate it with: python web/tiger/snapshot.py --offline (or with TigerData credentials, ' +
      'python web/tiger/ingest.py then python web/tiger/snapshot.py). Nothing is shown in its place.'));
    mount.appendChild(block);
  }

  function boot() {
    var mount = document.getElementById('tiger-chart') || document.querySelector('[data-tiger-chart]');
    if (!mount) return;
    var src = mount.getAttribute('data-snapshot') ||
      (script && script.src ? new URL('snapshot.json', script.src).href : 'snapshot.json');
    mount.appendChild(el('p', 'tgr-note', 'Loading run-log snapshot…'));
    fetch(src, { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (snap) { render(mount, snap); })
      .catch(function (err) { showError(mount, err.message); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();

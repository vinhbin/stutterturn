'use strict';

(async function () {
  const root = document.querySelector('#model-comparison');
  if (!root) return;
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const seconds = value => Number(value).toFixed(3) + ' s';
  const svgNode = (tag, attrs, text) => {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    if (text !== undefined) el.textContent = text;
    return el;
  };
  const labels = {
    speech_start: 'Speech detected', speech_stop: 'Speech stopped',
    turn_complete: 'Decided to reply', turn_incomplete: 'Held the turn',
    speaker_resumed: 'Resumption after a reply decision',
    agent_audio_start: 'Reply audio scheduled', agent_audio_end: 'Reply audio ended',
    cancelled: 'Reply cancelled', timeout: 'Provider timeout'
  };
  try {
    const response = await fetch(root.dataset.snapshot);
    if (!response.ok) throw new Error('Snapshot unavailable');
    const data = await response.json();
    const runs = data.runs;
    if (data.schema_version !== 1 || data.offline_fallback !== false || !data.generated_utc || !data.query_sha256 ||
        !Array.isArray(runs) || runs.length !== 2 || runs[0].config !== 'stock_fp32' || runs[1].config !== 'candidate' ||
        runs[0].source_id !== runs[1].source_id || runs.some(r => !Array.isArray(r.events) || r.reason !== 'completed')) {
      throw new Error('Invalid snapshot provenance');
    }
    const [stock, ours] = runs;
    // This explanation belongs to this exact recorded case, not any future pair.
    if (stock.run_id !== '20261011T053423Z-stock_fp32-bbcf' || ours.run_id !== '20261011T053442Z-candidate-efd3' ||
        stock.first_decision_name !== 'turn_complete' || ours.first_decision_name !== 'turn_incomplete' ||
        stock.first_decision_t !== ours.first_decision_t) throw new Error('Unexpected comparison');
    const content = document.createDocumentFragment();
    content.append(node('p', 'Our model held the early pause.', 'cmp-takeaway'));
    content.append(node('p', `At ${seconds(stock.first_decision_t)}, Stock FP32 decided to reply. Our X1 configuration kept listening until speech continued. Same recording. Same ${stock.params.vad_stop_s.toFixed(1)} s silence gate.`, 'snapshot-intro'));
    const firstAudio = stock.events.find(e => e.name === 'agent_audio_start');
    const firstResumption = stock.events.find(e => e.name === 'speaker_resumed');
    if (!firstAudio || !firstResumption) throw new Error('Missing comparison events');
    content.append(node('p', `Stock scheduled its reply at ${seconds(firstAudio.t)}; speech resumed at ${seconds(firstResumption.t)}. X1 avoided that early reply.`, 'snapshot-intro'));
    content.append(node('p', 'Saved Tiger Data query · ' + data.generated_utc + ' · 2 Vultr runs · ' + stock.source_duration_s + ' s source', 'cmp-provenance'));

    const figure = node('figure', undefined, 'cmp-figure');
    figure.append(node('figcaption', 'One source, two decisions. Timelines share the same clock.'));
    const svg = svgNode('svg', {viewBox: '0 0 920 280', 'aria-hidden': 'true', focusable: 'false'});
    const duration = stock.source_duration_s + stock.params.trailing_silence_s;
    const x = t => 170 + t / duration * 730;
    svg.append(svgNode('rect', {x: 170, y: 30, width: x(stock.source_duration_s) - 170, height: 200, class: 'cmp-source'}));
    svg.append(svgNode('text', {x: 180, y: 23, class: 'cmp-axis'}, 'Source recording · 10.4 s'));
    svg.append(svgNode('text', {x: x(stock.source_duration_s) + 8, y: 23, class: 'cmp-axis'}, '5 s silence padding'));
    for (let t = 0; t <= 15; t += 3) {
      svg.append(svgNode('line', {x1: x(t), x2: x(t), y1: 35, y2: 225, class: 'cmp-grid'}));
      svg.append(svgNode('text', {x: x(t), y: 260, 'text-anchor': 'middle', class: 'cmp-axis'}, t + ' s'));
    }
    runs.forEach((run, index) => {
      const y = 85 + index * 100;
      svg.append(svgNode('text', {x: 0, y: y + 5, class: index ? 'cmp-ours-label' : 'cmp-label'}, index ? 'Our model · X1' : 'Stock FP32'));
      svg.append(svgNode('line', {x1: 170, x2: 900, y1: y, y2: y, class: 'cmp-baseline'}));
      run.events.forEach((event, i) => {
        if (event.name === 'turn_incomplete') {
          const nextSpeech = run.events.slice(i + 1).find(e => e.name === 'speech_start');
          if (nextSpeech) svg.append(svgNode('rect', {x: x(event.t), y: y - 7, width: x(nextSpeech.t) - x(event.t), height: 14, class: 'cmp-hold'}));
        }
        if (event.name === 'agent_audio_start') {
          const end = run.events.slice(i + 1).find(e => e.name === 'agent_audio_end');
          if (end) svg.append(svgNode('rect', {x: x(event.t), y: y - 7, width: Math.max(3, x(end.t) - x(event.t)), height: 14, class: 'cmp-audio'}));
        }
        if (event.name === 'turn_complete') svg.append(svgNode('circle', {cx: x(event.t), cy: y, r: 6, class: 'cmp-decision'}));
        if (event.name === 'speech_start' && event.t > 1) svg.append(svgNode('path', {d: `M${x(event.t)} ${y - 16}v32`, class: 'cmp-speech'}));
        if (event.name === 'timeout') svg.append(svgNode('text', {x: x(event.t), y: y - 22, 'text-anchor': 'middle', class: 'cmp-timeout'}, 'Gemini timeout'));
      });
    });
    figure.append(svg);
    figure.append(node('p', '● Reply decision    ┃ Speech detected    Green bar: holding    Blue bar: scheduled reply audio', 'cmp-legend'));
    content.append(figure);

    const wrap = node('div', undefined, 'snapshot-comparison');
    wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Stock FP32 versus our model results');
    const table = node('table');
    table.append(node('caption', 'Observed in this replay · audio times use the server sample schedule'));
    const head = node('thead'); const headers = node('tr');
    ['Recorded observation', 'Stock FP32', 'Our model · X1'].forEach(text => { const th = node('th', text); th.scope = 'col'; headers.append(th); });
    head.append(headers); table.append(head);
    const body = node('tbody');
    const cells = [
      ['First pause, at ' + seconds(stock.first_decision_t), 'Decided to reply', 'Held the turn'],
      ['Reported audio overlap', seconds(stock.reported_overlap_s), ours.reported_overlap_s === null ? 'None reported' : seconds(ours.reported_overlap_s)],
      ['Later pause, at 7.072 s', 'Decided; cancelled before audio', 'Decided; cancelled before audio'],
      ['Provider timeouts', stock.timeouts.join(', ') || 'None', ours.timeouts.join(', ') || 'None'],
      ['Decision threshold', String(stock.params.threshold), String(ours.params.threshold)]
    ];
    cells.forEach(values => { const tr = node('tr'); values.forEach((text, i) => { const cell = node(i ? 'td' : 'th', text); if (!i) cell.scope = 'row'; tr.append(cell); }); body.append(tr); });
    table.append(body); wrap.append(table); content.append(wrap);
    content.append(node('p', 'This selected replay shows X1 avoiding one early reply. Both configurations still decided before later detected resumption at 7.680 s. X1 changes the model and threshold; this does not isolate a gain from the weights alone. The stock Gemini timeout is a provider outcome, not a model-quality result.', 'cmp-context'));
    content.append(node('p', 'X1 is exploratory and unpromoted. These are scheduled audio events, not measured acoustic timing or a general interruption rate. A longer-wait baseline remains below as separate historical evidence.', 'cmp-context'));

    const detail = node('details', undefined, 'cmp-details');
    detail.append(node('summary', 'Inspect all comparison events and model identities'));
    runs.forEach((run, index) => {
      const section = node('section'); section.append(node('h3', index ? 'Our model · X1' : 'Stock FP32'));
      section.append(node('p', 'Run ' + run.run_id + ' · backend ' + run.commit_sha));
      section.append(node('p', 'Model: ' + run.model + ' · SHA-256: ' + run.model_sha256));
      const events = node('ol');
      run.events.forEach(event => {
        const info = [seconds(event.t), labels[event.name], event.before_audible === true ? 'before audio' : '',
          event.service || '', event.prob !== null && event.threshold !== null ? `p=${event.prob}, threshold=${event.threshold}` : ''].filter(Boolean).join(' · ');
        events.append(node('li', info));
      });
      section.append(events); detail.append(section);
    });
    content.append(detail);
    root.replaceChildren(content);
  } catch (_) {
    const message = node('p', 'The saved comparison could not be loaded. Read the saved data or try again; no results are being inferred.', 'cmp-context');
    root.replaceChildren(message);
  }
})();

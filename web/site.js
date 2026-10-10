'use strict';

// The judge view embeds the same console, including its source and playback notices.
const consoleFrame = document.querySelector('#console-frame');
let consoleObserver;

function fitConsole() {
  const frameDocument = consoleFrame?.contentDocument;
  if (!frameDocument?.body) return;
  consoleObserver?.disconnect();

  frameDocument.documentElement.classList.add('embedded-console');
  consoleFrame.contentWindow.dispatchEvent(new Event('resize'));

  let scheduled = false;
  const resize = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      const height = Math.ceil(frameDocument.body.getBoundingClientRect().height) + 2;
      if (Math.abs(consoleFrame.getBoundingClientRect().height - height) > 1) {
        consoleFrame.style.height = `${height}px`;
      }
    });
  };
  consoleObserver = new ResizeObserver(resize);
  consoleObserver.observe(frameDocument.body);
  resize();
  frameDocument.fonts.ready.then(resize);
}

if (consoleFrame) {
  consoleFrame.addEventListener('load', fitConsole);
  if (consoleFrame.contentDocument?.readyState === 'complete') fitConsole();
}

// This seekable illustration represents no recorded timing or audio.
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const turnFigure = document.querySelector('.turn-figure');

if (turnFigure) {
  const loopClock = document.querySelector('#loop-clock');
  const toggle = document.querySelector('#sequence-toggle');
  const slider = document.querySelector('#sequence-position');
  const phaseLabel = document.querySelector('#sequence-phase');
  const note = document.querySelector('#sequence-note');
  const CYCLE_MS = 7500;
  const SEQUENCE_MS = 6000;
  let position = 100;
  let playing = false;
  let startedAt = 0;
  let frame = null;
  let inView = false;
  let userPaused = reducedMotion.matches;
  document.querySelector('.sequence-transport').hidden = false;

  const render = (percent) => {
    position = percent;
    const phase = percent < 32 ? 'Speaking' : percent < 51 ? 'Pause' : percent < 82 ? 'Continuing' : 'Reply';
    const descriptions = {
      Speaking: 'The caller is speaking. The agent keeps listening.',
      Pause: 'A pause can belong to an unfinished turn. The agent holds.',
      Continuing: 'The caller continues the same thought. Keep the turn open.',
      Reply: 'The caller has finished. Now the agent can reply.',
    };
    const elapsed = percent * SEQUENCE_MS / 100000;
    loopClock.textContent = `00:0${elapsed.toFixed(2)}`;
    slider.value = String(Math.round(percent));
    slider.setAttribute('aria-valuetext', `${phase}, ${Math.round(percent)} percent through the illustration`);
    phaseLabel.textContent = phase;
    note.textContent = descriptions[phase];
    turnFigure.style.setProperty('--sequence-progress', `${percent}%`);
    turnFigure.style.setProperty('--wait-visible', percent >= 32 ? '1' : '0');
    turnFigure.style.setProperty('--reply-visible', percent >= 82 ? '1' : '0');
    turnFigure.style.setProperty('--speaking-visible', phase === 'Speaking' || phase === 'Continuing' ? '1' : '0');
    turnFigure.style.setProperty('--holding-visible', phase === 'Pause' ? '1' : '0');
  };

  const updateButton = () => {
    const label = playing ? 'Pause illustration' : 'Play illustration';
    toggle.querySelector('span').textContent = label;
    toggle.setAttribute('aria-label', label);
    turnFigure.classList.toggle('is-playing', playing);
  };
  const pause = () => {
    playing = false;
    cancelAnimationFrame(frame);
    updateButton();
  };
  const tick = (now) => {
    if (!playing) return;
    const elapsed = (now - startedAt) % CYCLE_MS;
    render(Math.min(elapsed / SEQUENCE_MS * 100, 100));
    frame = requestAnimationFrame(tick);
  };
  const play = () => {
    if (playing || document.hidden) return;
    playing = true;
    startedAt = performance.now() - (position === 100 ? 0 : position / 100 * SEQUENCE_MS);
    updateButton();
    frame = requestAnimationFrame(tick);
  };

  toggle.addEventListener('click', () => {
    userPaused = playing;
    if (playing) pause(); else play();
  });
  slider.addEventListener('input', () => {
    userPaused = true;
    pause();
    render(Number(slider.value));
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      if (inView && !userPaused) play(); else pause();
    }, { threshold: 0.25 }).observe(turnFigure);
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) pause(); else if (inView && !userPaused) play();
  });
  reducedMotion.addEventListener('change', (event) => {
    if (event.matches) { userPaused = true; pause(); }
  });
  render(100);
}

'use strict';

// The judge view embeds the same console, including its source and playback notices.
const consoleFrame = document.querySelector('#console-frame');
let consoleObserver;

function fitConsole() {
  const frameDocument = consoleFrame?.contentDocument;
  if (!frameDocument?.body) return;
  consoleObserver?.disconnect();

  const style = frameDocument.createElement('style');
  style.textContent = 'body { max-width: none; padding: 0 0 20px !important; } .page-header { min-height: 32px; padding-top: 8px; border: 0; justify-content: flex-end; } .page-header .identity, .header-meta > span { display: none; } .header-meta { max-width: none !important; } @media (min-width: 1001px) { .page-header { min-height: 26px; padding-top: 0; } .status-banner { min-height: 36px; padding-block: 8px; } }';
  frameDocument.head.append(style);

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

// Landing page: concept-loop playback and section reveals.
// The loop is an illustrative sequence; it represents no recorded timing or audio.
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const turnFigure = document.querySelector('.turn-figure');

if (turnFigure && !reducedMotion.matches && 'IntersectionObserver' in window) {
  const loopClock = document.querySelector('#loop-clock');
  const CYCLE_MS = 7500; // matches the CSS loop-* animation duration
  const WIPE_MS = 6000;  // reveal completes at 80% of the cycle, then holds
  let startedAt = null;
  let frame = null;

  const renderClock = (now) => {
    const elapsed = Math.min((now - startedAt) % CYCLE_MS, WIPE_MS) / 1000;
    const whole = Math.floor(elapsed);
    const centis = Math.floor((elapsed - whole) * 100);
    loopClock.textContent = `00:0${whole}.${String(centis).padStart(2, '0')}`;
    frame = requestAnimationFrame(renderClock);
  };

  const play = () => {
    if (startedAt !== null) return;
    turnFigure.classList.add('is-playing');
    startedAt = performance.now();
    frame = requestAnimationFrame(renderClock);
  };

  const pause = () => {
    if (startedAt === null) return;
    turnFigure.classList.remove('is-playing');
    cancelAnimationFrame(frame);
    startedAt = null;
    loopClock.textContent = '00:06.00';
  };

  new IntersectionObserver((entries) => {
    entries.forEach((entry) => (entry.isIntersecting ? play() : pause()));
  }, { threshold: 0.25 }).observe(turnFigure);

  reducedMotion.addEventListener?.('change', (event) => { if (event.matches) pause(); });
}

if (document.body.classList.contains('landing') && !reducedMotion.matches && 'IntersectionObserver' in window) {
  const revealed = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-revealed');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.body.classList.add('reveal-armed');
  document.querySelectorAll('[data-reveal]').forEach((section) => revealed.observe(section));
}

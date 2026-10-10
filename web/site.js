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

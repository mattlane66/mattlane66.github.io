/* Native dialog: keyboard Escape, focus containment, and no runtime dependency. */
(function () {
  'use strict';
  const trigger = document.getElementById('site-design-info-trigger');
  const dialog = document.getElementById('site-design-info-dialog');
  const closeButton = dialog && dialog.querySelector('.design-info-close');
  if (!trigger || !dialog || !closeButton || typeof dialog.showModal !== 'function') return;

  let previousFocus = null;
  trigger.addEventListener('click', function () {
    if (dialog.open) return;
    previousFocus = document.activeElement;
    dialog.showModal();
    closeButton.focus({ preventScroll: true });
  });
  closeButton.addEventListener('click', function () {
    dialog.close();
  });
  dialog.addEventListener('click', function (event) {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom) {
      dialog.close();
    }
  });
  dialog.addEventListener('close', function () {
    const target = previousFocus && previousFocus.isConnected ? previousFocus : trigger;
    target.focus({ preventScroll: true });
    previousFocus = null;
  });
}());

document.addEventListener('DOMContentLoaded', function () {
  function setActivePhoto(photoId) {
    if (!photoId) return;
    const controlsPane = document.getElementById('controls-photo-' + photoId);
    const viewerPane = document.getElementById('viewer-photo-' + photoId);
    document.querySelectorAll('.photo-controls-content .tab-pane').forEach(function (pane) {
      pane.classList.remove('show', 'active');
    });
    document.querySelectorAll('.photo-viewer-content .tab-pane').forEach(function (pane) {
      pane.classList.remove('show', 'active');
    });
    if (controlsPane) controlsPane.classList.add('show', 'active');
    if (viewerPane) viewerPane.classList.add('show', 'active');

    const activeAnalysis = controlsPane ? controlsPane.querySelector('.analysis-tab-button.active') : null;
    if (activeAnalysis) {
      const viewerTarget = activeAnalysis.getAttribute('data-viewer-target');
      if (viewerTarget) {
        const targetPane = document.querySelector(viewerTarget);
        const viewerContent = targetPane ? targetPane.closest('.viewer-tab-content') : null;
        if (viewerContent && targetPane) {
          viewerContent.querySelectorAll('.tab-pane').forEach(function (pane) {
            pane.classList.remove('show', 'active');
          });
          targetPane.classList.add('show', 'active');
        }
      }
    }
  }

  // initial sync to the active photo
  const initialActive = document.querySelector('.photo-tab-button.active');
  if (initialActive) setActivePhoto(initialActive.getAttribute('data-photo-id'));

  // sync photo tabs (left list) with controls pane and viewer pane
  document.querySelectorAll('.photo-tab-button').forEach(function (btn) {
    btn.addEventListener('shown.bs.tab', function () {
      setActivePhoto(btn.getAttribute('data-photo-id'));
    });
    btn.addEventListener('click', function () {
      setTimeout(function () {
        setActivePhoto(btn.getAttribute('data-photo-id'));
      }, 0);
    });
  });

  // sync analysis tabs (left) with viewer panes (right)
  document.querySelectorAll('.analysis-tab-button').forEach(function (btn) {
    btn.addEventListener('shown.bs.tab', function () {
      const viewerTarget = btn.getAttribute('data-viewer-target');
      const infoTarget = btn.getAttribute('data-info-target');
      if (!viewerTarget) return;
      const targetPane = document.querySelector(viewerTarget);
      if (!targetPane) return;
      const viewerContent = targetPane.closest('.viewer-tab-content');
      if (!viewerContent) return;
      viewerContent.querySelectorAll('.tab-pane').forEach(function (pane) {
        pane.classList.remove('show', 'active');
      });
      targetPane.classList.add('show', 'active');

      if (infoTarget) {
        const infoPane = document.querySelector(infoTarget);
        const infoContent = infoPane ? infoPane.closest('.analysis-info') : null;
        if (infoContent && infoPane) {
          infoContent.querySelectorAll('.tab-pane').forEach(function (pane) {
            pane.classList.remove('show', 'active');
          });
          infoPane.classList.add('show', 'active');
        }
      }
    });
  });

  document.querySelectorAll('.rename-photo-btn').forEach(function (btn) {
    btn.addEventListener('click', async function (ev) {
      ev.preventDefault();
      const photoId = btn.getAttribute('data-photo-id');
      if (!photoId) return;
      const taskId = window.location.pathname.split('/').filter(Boolean)[1];
      const currentTitleEl = document.querySelector('.photo-title[data-photo-id="' + photoId + '"]');
      const current = currentTitleEl ? currentTitleEl.textContent.trim() : '';
      const newTitle = prompt('Введите новое название для вкладки', current || '');
      if (newTitle === null) return; // cancelled

      try {
        const fd = new FormData();
        fd.append('new_title', newTitle);
        const resp = await fetch(`/tasks/${taskId}/photos/${photoId}/rename`, {
          method: 'POST',
          body: fd,
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
          if (currentTitleEl) currentTitleEl.textContent = data.title || newTitle;
        } else {
          alert('Не удалось переименовать: ' + (data.error || 'ошибка'));
        }
      } catch (err) {
        alert('Ошибка запроса: ' + String(err));
      }
    });
  });
});

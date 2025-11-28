document.addEventListener('DOMContentLoaded', function () {
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

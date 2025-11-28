document.addEventListener('DOMContentLoaded', function () {
  const img = document.getElementById('mainTaskImage');
  const input = document.getElementById('analyze_photo_input');
  const form = document.getElementById('analyzeForm');

  if (img && input) {
    if (!input.value) input.value = img.getAttribute('src') || '';
    img.addEventListener('click', () => {
      input.value = img.getAttribute('src') || '';
    });
  }

  document.querySelectorAll('.task-photo-thumb').forEach(function (thumb) {
    thumb.addEventListener('click', function (ev) {
      const src = thumb.getAttribute('data-src') || thumb.getAttribute('src');
      if (src && input) input.value = src;
    });
  });

  if (!form) return;

    document.querySelectorAll('.hsv-form').forEach(function (formEl) {
      const tab = formEl.closest('.tab-pane');
      const msg = document.createElement('div');
      msg.className = 'hsv-message mt-2';
      // insert after the form; use insertAdjacentElement to avoid parent mismatches
      try { formEl.insertAdjacentElement('afterend', msg); } catch (e) { if (tab) tab.appendChild(msg); }

      formEl.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        msg.innerHTML = '';

        const photoInput = formEl.querySelector('input[name="photo_path"]');
        const photoId = photoInput ? String(photoInput.value || '').trim() : '';
        if (!photoId) {
          msg.innerHTML = '<div class="alert alert-danger">Не указано изображение для анализа.</div>';
          return;
        }

        const hueLow = parseFloat(formEl.querySelector('input[name="hue_low"]').value || '0');
        const hueHigh = parseFloat(formEl.querySelector('input[name="hue_high"]').value || '0');
        const satMin = parseFloat(formEl.querySelector('input[name="sat_min"]').value || '0');
        const valMin = parseFloat(formEl.querySelector('input[name="val_min"]').value || '0');
        if (!(satMin >= 0 && satMin <= 1 && valMin >= 0 && valMin <= 1)) {
          msg.innerHTML = '<div class="alert alert-danger">Sat и Val должны быть в диапазоне 0..1</div>';
          return;
        }
        if (!(hueLow >= 0 && hueLow <= 360 && hueHigh >= 0 && hueHigh <= 360)) {
          msg.innerHTML = '<div class="alert alert-danger">Hue должен быть в диапазоне 0..360</div>';
          return;
        }

        // Build FormData and ensure photo_path is the numeric id
        const fd = new FormData(formEl);
        fd.set('photo_path', photoId);

        // Remember active tab to restore it after DOM updates
        const activeBtn = tab ? tab.parentElement.querySelector('.nav-link.active') : document.querySelector('.nav-link.active');

        let resp, data;
        try {
          resp = await fetch(formEl.action, {
            method: 'POST',
            body: fd,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          });
        } catch (err) {
          msg.innerHTML = '<div class="alert alert-danger">Ошибка запроса: ' + String(err) + '</div>';
          return;
        }

        const ctype = resp.headers.get('content-type') || '';
        if (resp.ok && ctype.indexOf('application/json') !== -1) {
          try { data = await resp.json(); } catch (e) { data = null; }
        } else {
          // Non-JSON response (likely a redirect). Show generic error.
          const text = await resp.text().catch(()=>'');
          msg.innerHTML = '<div class="alert alert-danger">Сервер вернул не-JSON ответ (status=' + resp.status + ').</div>' + (text ? '<pre style="max-height:200px;overflow:auto">' + text.substring(0,1000) + '</pre>' : '');
          return;
        }

        if (data && data.success && data.path) {
          // find or create image element inside the same tab
          let outImg = tab.querySelector('img.hsv-result[data-photo-id="' + photoId + '"]');
          if (!outImg) {
            outImg = document.createElement('img');
            outImg.className = 'img-fluid hsv-result mt-2';
            outImg.setAttribute('data-photo-id', photoId);
            // insert before the message node
            if (msg && msg.parentNode) msg.parentNode.insertBefore(outImg, msg);
            else if (tab) tab.appendChild(outImg);
          }
          outImg.src = data.path + '?t=' + Date.now();
          msg.innerHTML = '<div class="alert alert-success">Анализ выполнен</div>';

          // restore active tab (Bootstrap)
          try { if (activeBtn && typeof bootstrap !== 'undefined') bootstrap.Tab.getOrCreateInstance(activeBtn).show(); } catch(e){}
        } else {
          const err = data && data.error ? data.error : 'Неизвестная ошибка';
          msg.innerHTML = '<div class="alert alert-danger">Ошибка: ' + (err) + '</div>';
        }
      });
    });

    // Rename buttons handling (keep existing behavior)
    document.querySelectorAll('.rename-photo-btn').forEach(function (btn) {
      btn.addEventListener('click', async function (ev) {
        const photoId = btn.getAttribute('data-photo-id');
        const currentSpan = document.querySelector('.photo-title[data-photo-id="' + photoId + '"]');
        const current = currentSpan ? currentSpan.textContent.trim() : '';
        const newTitle = prompt('Новое название вкладки:', current || '');
        if (newTitle === null) return; // cancelled

        const fd = new FormData();
        fd.append('new_title', newTitle);
        try {
          const resp = await fetch(`/tasks/${window.location.pathname.split('/')[2]}/photos/${photoId}/rename`, {
            method: 'POST',
            body: fd,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          });
          const data = await resp.json();
          if (resp.ok && data.success) {
            if (currentSpan) currentSpan.textContent = data.title || newTitle;
            const tabBtn = document.getElementById('photo-tab-' + photoId);
            if (tabBtn) {
              const titleSpan = tabBtn.querySelector('.photo-title');
              if (titleSpan) titleSpan.textContent = data.title || newTitle;
              else tabBtn.textContent = data.title || newTitle;
            }
          } else {
            alert('Ошибка при переименовании: ' + (data.error || 'unknown'));
          }
        } catch (err) {
          alert('Ошибка запроса: ' + err);
        }
      });
    });
  });
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.ndvi-form').forEach(function (form) {
    const tab = form.closest('.tab-pane');
    const msg = document.createElement('div');
    msg.className = 'ndvi-message mt-2';
    form.parentNode.insertBefore(msg, form.nextSibling);

    const palette = form.querySelector('.band-palette');
    if (palette) {
      palette.querySelectorAll('.band-chip').forEach(function (chip) {
        chip.addEventListener('click', function () {
          const name = chip.getAttribute('data-band-name');
          const idx = chip.getAttribute('data-band-index');
          const active = document.activeElement;
          if (active && active.classList && active.classList.contains('band-target')) {
            if (active.type === 'number') active.value = idx; else active.value = name;
            active.dispatchEvent(new Event('input'));
            return;
          }
          const targets = Array.from(form.querySelectorAll('.band-target'));
          let filled = false;
          for (const t of targets) {
            if (!t.value) {
              if (t.type === 'number') t.value = idx; else t.value = name;
              t.dispatchEvent(new Event('input'));
              filled = true;
              break;
            }
          }
          if (!filled && targets.length) {
            const t = targets[0];
            if (t.type === 'number') t.value = idx; else t.value = name;
            t.dispatchEvent(new Event('input'));
          }
        });

        chip.addEventListener('dragstart', function (e) {
          e.dataTransfer.setData('text/plain', chip.getAttribute('data-band-name'));
          e.dataTransfer.setData('application/x-band-index', chip.getAttribute('data-band-index'));
        });
      });

      form.querySelectorAll('.band-target').forEach(function (input) {
        input.addEventListener('dragover', function (e) { e.preventDefault(); });
        input.addEventListener('drop', function (e) {
          e.preventDefault();
          const name = e.dataTransfer.getData('text/plain');
          const idx = e.dataTransfer.getData('application/x-band-index');
          if (input.type === 'number') input.value = idx; else input.value = name;
          input.dispatchEvent(new Event('input'));
        });
      });
    }

    form.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      msg.innerHTML = '';
      const fd = new FormData(form);
      try {
        // remember active tab button so we can restore it after DOM updates
        const activeBtn = tab.querySelector('.photo-tab-button.active') || document.querySelector('.nav-link.active');
        const resp = await fetch(form.action, {
          method: 'POST',
          body: fd,
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
          const photoIdInput = form.querySelector('input[name="photo_path"]');
          const photoId = photoIdInput ? photoIdInput.value : null;
          let outImg = null;
          if (photoId) {
            const viewerPane = document.getElementById('viewer-ndvi-pane-' + photoId);
            if (viewerPane) {
              outImg = viewerPane.querySelector('img.ndvi-result');
              if (!outImg) {
                outImg = document.createElement('img');
                outImg.className = 'img-fluid rounded mb-2 ndvi-result';
                viewerPane.innerHTML = '';
                viewerPane.appendChild(outImg);
              }
            }
          }
          if (!outImg) {
            outImg = tab ? tab.querySelector('img.ndvi-result') : null;
            if (!outImg) {
              outImg = document.createElement('img');
              outImg.className = 'img-fluid ndvi-result mt-2';
              if (msg && msg.parentNode) {
                msg.parentNode.insertBefore(outImg, msg);
              } else if (tab) {
                tab.appendChild(outImg);
              }
            }
          }
          outImg.src = data.path + '?t=' + Date.now();
          msg.innerHTML = '<div class="alert alert-success">NDVI выполнен (Результат сохраниться после перезагрузки страницы)</div>';
          // restore active tab (Bootstrap may reset active state when DOM changes)
          try {
            if (activeBtn && typeof bootstrap !== 'undefined') {
              const tabInstance = bootstrap.Tab.getOrCreateInstance(activeBtn);
              tabInstance.show();
            }
          } catch (e) {
            // ignore if bootstrap not available
          }
        } else {
          const err = (data && data.error) ? data.error : 'Неизвестная ошибка';
          msg.innerHTML = '<div class="alert alert-danger">Ошибка: ' + err + '</div>';
        }
      } catch (err) {
        msg.innerHTML = '<div class="alert alert-danger">Ошибка запроса: ' + String(err) + '</div>';
      }
    });
  });
});
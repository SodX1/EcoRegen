document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.segm-form').forEach(function (form) {
    const tab = form.closest('.tab-pane');
    const msg = document.createElement('div');
    msg.className = 'segm-message mt-2';
    form.parentNode.insertBefore(msg, form.nextSibling);

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
            const viewerPane = document.getElementById('viewer-segm-pane-' + photoId);
            if (viewerPane) {
              outImg = viewerPane.querySelector('img.segm-result');
              if (!outImg) {
                outImg = document.createElement('img');
                outImg.className = 'img-fluid rounded mb-2 segm-result';
                viewerPane.innerHTML = '';
                viewerPane.appendChild(outImg);
              }
            }
          }
          if (!outImg) {
            outImg = tab ? tab.querySelector('img.segm-result') : null;
            if (!outImg) {
              outImg = document.createElement('img');
              outImg.className = 'img-fluid segm-result mt-2';
              if (msg && msg.parentNode) {
                msg.parentNode.insertBefore(outImg, msg);
              } else if (tab) {
                tab.appendChild(outImg);
              }
            }
          }
          outImg.src = data.path + '?t=' + Date.now();
          msg.innerHTML = '<div class="alert alert-success">Сегментация выполнена</div>';
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

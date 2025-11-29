document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.ndvi-form').forEach(function (form) {
    const tab = form.closest('.tab-pane');
    const msg = document.createElement('div');
    msg.className = 'ndvi-message mt-2';
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
          let outImg = tab.querySelector('img.ndvi-result');
          if (!outImg) {
            outImg = document.createElement('img');
            outImg.className = 'img-fluid ndvi-result mt-2';
            // insert outImg next to the message node (same parent)
            if (msg && msg.parentNode) {
              msg.parentNode.insertBefore(outImg, msg);
            } else if (tab) {
              tab.appendChild(outImg);
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
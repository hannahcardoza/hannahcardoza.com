// Footer visitor counter, powered by GoatCounter's public counter.
// Requires "Allow adding visitor counts on your website" in GoatCounter settings.
(function () {
  var el = document.getElementById('visitor-count');
  if (!el) return;
  fetch('https://hannahcardoza.goatcounter.com/counter/TOTAL.json')
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (d) {
      var n = String(d.count).replace(/\D/g, '');
      if (n) el.textContent = n.padStart(6, '0');
    })
    .catch(function () {});
})();

// One-time welcome popup. Shown on a visitor's first page view only.
// If browser storage is unavailable (private mode, blocked), it is skipped
// rather than shown on every page.
(function () {
  var KEY = 'hc-welcomed';
  try {
    if (localStorage.getItem(KEY)) return;
    localStorage.setItem(KEY, '1');
  } catch (e) {
    return;
  }
  var d = document.createElement('dialog');
  if (typeof d.showModal !== 'function') return;
  d.className = 'welcome-pop';
  d.setAttribute('aria-labelledby', 'welcome-title');
  d.innerHTML =
    '<div class="bar"><span id="welcome-title">welcome.exe</span>' +
    '<button type="button" data-close aria-label="Close">×</button></div>' +
    '<div class="body"><p>Welcome to the new website.</p>' +
    '<button type="button" class="ok" data-close autofocus>OK</button></div>';
  document.body.appendChild(d);
  d.addEventListener('click', function (e) {
    if (e.target === d || e.target.hasAttribute('data-close')) d.close();
  });
  d.addEventListener('close', function () { d.remove(); });
  d.showModal();
})();

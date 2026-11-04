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
    '<div class="bar"><span id="welcome-title">welcome.exe</span></div>' +
    '<div class="body"><p>Welcome to the new site!</p>' +
    '<button type="button" class="ok" data-close autofocus>OK</button></div>';
  document.body.appendChild(d);
  d.addEventListener('click', function (e) {
    if (e.target === d || e.target.hasAttribute('data-close')) d.close();
  });
  d.addEventListener('close', function () { d.remove(); });
  d.showModal();
})();

// Slim sticky nav that slides in once the big rainbow tabs scroll out of view.
// Built from the page's own nav, so every page gets it without extra markup.
(function () {
  var nav = document.querySelector('header nav');
  if (!nav) return;
  var labels = {
    '/': ['Introduction', 'Intro'],
    '/about': ['About Me', 'About'],
    '/experience': ['Experience', 'Exp'],
    '/web-log': ['Web Log', 'Log']
  };
  var colors = ['klein', 'fuchsia', 'tangerine', 'citric'];
  var items = Array.prototype.map.call(nav.querySelectorAll('a'), function (a) {
    var href = a.getAttribute('href').replace(/\/$/, '') || '/';
    var label = labels[href] || [a.textContent, a.textContent];
    var color = colors.filter(function (c) { return a.classList.contains('bg-' + c); })[0] || 'cream';
    var current = a.getAttribute('aria-current') ? ' aria-current="page"' : '';
    return '<li><a class="mini-' + color + '" href="' + a.getAttribute('href') + '"' + current + '>' +
      '<span class="full">' + label[0] + '</span><span class="short">' + label[1] + '</span></a></li>';
  }).join('');
  var bar = document.createElement('nav');
  bar.className = 'mini-nav';
  bar.setAttribute('aria-label', 'Quick navigation');
  bar.inert = true;
  bar.innerHTML = '<div class="mini-inner"><a class="mini-name" href="/">' +
    '<span class="full">Hannah Cardoza</span><span class="short">HC</span></a><ul>' + items + '</ul></div>';
  document.body.appendChild(bar);
  var ticking = false;
  function update() {
    ticking = false;
    var show = nav.getBoundingClientRect().bottom < 0;
    if (show !== bar.classList.contains('show')) {
      bar.classList.toggle('show', show);
      bar.inert = !show;
    }
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();
})();

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

// HC-FM: a small internet radio window streaming SomaFM (listener-supported,
// commercial-free; https://somafm.com). Opens from the RADIO button, never
// autoplays, and remembers station, volume, and open state between pages.
(function () {
  var STATIONS = [
    ['vaporwaves', 'Vaporwaves', 'Vaporwave, future funk'],
    ['groovesalad', 'Groove Salad', 'Ambient downtempo'],
    ['secretagent', 'Secret Agent', 'Spy lounge'],
    ['u80s', 'Underground 80s', 'Synthpop, new wave'],
    ['poptron', 'PopTron', 'Electropop, indie dance'],
    ['lush', 'Lush', 'Dreamy vocals, chillout'],
    ['defcon', 'DEF CON Radio', 'Music for hacking']
  ];
  var MIRRORS = ['ice6', 'ice2', 'ice5'];
  var KEY = 'hc-radio';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }
  var state = load();
  state.i = Math.min(Math.max(+state.i || 0, 0), STATIONS.length - 1);
  state.vol = typeof state.vol === 'number' ? state.vol : 0.6;

  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'radio-fab';
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-controls', 'radio');
  btn.innerHTML = '<span class="radio-dot" aria-hidden="true"></span>Radio';

  var win = document.createElement('section');
  win.id = 'radio';
  win.className = 'radio-pop';
  win.hidden = true;
  win.setAttribute('aria-label', 'HC-FM radio');
  win.innerHTML =
    '<div class="bar"><span>radio.exe</span><button type="button" class="radio-x" aria-label="Close radio">×</button></div>' +
    '<div class="radio-body">' +
    '<div class="radio-screen">' +
    '<div class="radio-top"><span class="radio-air">Off air</span><span class="radio-freq">HC-FM 20.01</span></div>' +
    '<div class="radio-eq" aria-hidden="true">' + new Array(16).join('<i></i>') + '<i></i></div>' +
    '<p class="radio-station"></p><p class="radio-genre"></p>' +
    '<p class="radio-now" aria-live="polite">Press play to tune in.</p>' +
    '</div>' +
    '<div class="radio-controls">' +
    '<button type="button" class="radio-prev" aria-label="Previous station">◀◀</button>' +
    '<button type="button" class="radio-play" aria-label="Play">▶</button>' +
    '<button type="button" class="radio-next" aria-label="Next station">▶▶</button>' +
    '<label class="radio-vol"><span class="sr-only">Volume</span><input type="range" min="0" max="1" step="0.05"></label>' +
    '</div>' +
    '<p class="radio-credit">Streaming <a href="https://somafm.com/" target="_blank" rel="noopener">SomaFM</a>, listener-supported radio. <a href="https://somafm.com/support/" target="_blank" rel="noopener">Support them</a>.</p>' +
    '</div>';
  document.body.appendChild(btn);
  document.body.appendChild(win);

  var $ = function (s) { return win.querySelector(s); };
  var playBtn = $('.radio-play'), vol = $('.radio-vol input');
  var audio = null, mirror = 0, metaTimer = null, playing = false;
  vol.value = state.vol;

  function station() { return STATIONS[state.i]; }
  function render() {
    $('.radio-station').textContent = station()[1];
    $('.radio-genre').textContent = station()[2];
    win.classList.toggle('on', playing);
    $('.radio-air').textContent = playing ? 'On air' : 'Off air';
    playBtn.textContent = playing ? '❚❚' : '▶';
    playBtn.setAttribute('aria-label', playing ? 'Pause' : 'Play');
    btn.classList.toggle('on', playing);
  }
  function setNow(text) { $('.radio-now').textContent = text; }

  function fetchMeta() {
    var id = station()[0];
    fetch('https://somafm.com/songs/' + id + '.json')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var s = d.songs && d.songs[0];
        if (s && playing && station()[0] === id) setNow('♪ ' + s.artist + ' – ' + s.title);
      })
      .catch(function () {});
  }

  function stop() {
    playing = false;
    if (audio) { audio.pause(); audio.removeAttribute('src'); audio.load(); }
    clearInterval(metaTimer);
    setNow('Press play to tune in.');
    render();
  }
  function play() {
    if (!audio) {
      audio = new Audio();
      audio.preload = 'none';
      audio.addEventListener('error', function () {
        if (!playing) return;
        mirror++;
        if (mirror < MIRRORS.length) start();
        else { stop(); setNow('Signal lost. Try another station.'); }
      });
    }
    mirror = 0;
    playing = true;
    start();
    clearInterval(metaTimer);
    fetchMeta();
    metaTimer = setInterval(fetchMeta, 30000);
  }
  function start() {
    audio.src = 'https://' + MIRRORS[mirror] + '.somafm.com/' + station()[0] + '-128-mp3';
    audio.volume = state.vol;
    setNow('Tuning in…');
    render();
    audio.play().catch(function (e) {
      if (e && e.name === 'NotAllowedError') { stop(); setNow('Press play to tune in.'); }
    });
  }
  function tune(step) {
    state.i = (state.i + step + STATIONS.length) % STATIONS.length;
    save();
    if (playing) play(); else render();
  }
  function open(show) {
    win.hidden = !show;
    btn.setAttribute('aria-expanded', String(show));
    state.open = show;
    save();
  }

  btn.addEventListener('click', function () { open(win.hidden); if (!win.hidden) playBtn.focus(); });
  $('.radio-x').addEventListener('click', function () { open(false); btn.focus(); });
  playBtn.addEventListener('click', function () { playing ? stop() : play(); });
  $('.radio-prev').addEventListener('click', function () { tune(-1); });
  $('.radio-next').addEventListener('click', function () { tune(1); });
  vol.addEventListener('input', function () {
    state.vol = +vol.value;
    if (audio) audio.volume = state.vol;
    save();
  });
  win.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { open(false); btn.focus(); }
  });

  render();
  if (state.open) open(true);
})();

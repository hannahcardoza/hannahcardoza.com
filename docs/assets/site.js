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

// HC-FM: a GTA-style car radio. Eight presets of real, freely streamed
// stations (Radio Swiss Jazz, FIP / Radio France, NTS, KEXP), a burst of
// static between stations, and live track info where the station shares it.
// Never autoplays. Remembers preset, volume, and open state between pages.
(function () {
  var STATIONS = [
    { freq: '88.1', name: 'Swiss Jazz', tag: 'Jazz, soul, and blues', src: 'Radio Swiss Jazz', site: 'https://www.radioswissjazz.ch/en',
      url: 'https://stream.srg-ssr.ch/m/rsj/mp3_128' },
    { freq: '90.7', name: 'FIP Jazz', tag: 'Jazz from Paris', src: 'FIP', site: 'https://www.radiofrance.fr/fip',
      url: 'https://icecast.radiofrance.fr/fipjazz-midfi.mp3', meta: ['fip', 65] },
    { freq: '93.3', name: 'FIP Groove', tag: 'Funk, soul, and hip-hop', src: 'FIP', site: 'https://www.radiofrance.fr/fip',
      url: 'https://icecast.radiofrance.fr/fipgroove-midfi.mp3', meta: ['fip', 66] },
    { freq: '96.9', name: 'NTS 1', tag: 'Underground radio, London', src: 'NTS', site: 'https://www.nts.live/',
      url: 'https://stream-relay-geo.ntslive.net/stream', meta: ['nts', 0] },
    { freq: '99.1', name: 'KEXP', tag: 'Indie and alternative, Seattle', src: 'KEXP', site: 'https://www.kexp.org/',
      url: 'https://kexp-mp3-128.streamguys1.com/kexp128.mp3', meta: ['kexp'] },
    { freq: '102.3', name: 'FIP Monde', tag: 'Bossa, Afrobeat, and beyond', src: 'FIP', site: 'https://www.radiofrance.fr/fip',
      url: 'https://icecast.radiofrance.fr/fipworld-midfi.mp3', meta: ['fip', 69] },
    { freq: '104.7', name: 'FIP Electro', tag: 'House, techno, and downtempo', src: 'FIP', site: 'https://www.radiofrance.fr/fip',
      url: 'https://icecast.radiofrance.fr/fipelectro-midfi.mp3', meta: ['fip', 74] },
    { freq: '107.5', name: 'FIP Reggae', tag: 'Reggae, dub, and ska', src: 'FIP', site: 'https://www.radiofrance.fr/fip',
      url: 'https://icecast.radiofrance.fr/fipreggae-midfi.mp3', meta: ['fip', 71] }
  ];
  var KEY = 'hc-radio';
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  var state = load();
  state.i = Math.min(Math.max(+state.i || 0, 0), STATIONS.length - 1);
  state.vol = typeof state.vol === 'number' ? state.vol : 0.6;

  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'radio-fab';
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-controls', 'radio');
  btn.innerHTML = '<span class="radio-dot" aria-hidden="true"></span>Radio';

  var presets = STATIONS.map(function (s, i) {
    return '<button type="button" class="radio-preset" data-i="' + i + '" aria-label="' + s.freq + ' ' + s.name + '">' + (i + 1) + '</button>';
  }).join('');
  var win = document.createElement('section');
  win.id = 'radio';
  win.className = 'radio-pop';
  win.hidden = true;
  win.setAttribute('aria-label', 'Radio');
  win.innerHTML =
    '<div class="bar"><span>radio.exe</span><button type="button" class="radio-x" aria-label="Close radio">×</button></div>' +
    '<div class="radio-body">' +
    '<div class="radio-screen">' +
    '<div class="radio-top"><span class="radio-air">Off air</span><span class="radio-band">FM stereo</span></div>' +
    '<div class="radio-main"><span class="radio-freq"></span><span class="radio-mhz">MHz</span>' +
    '<div class="radio-eq" aria-hidden="true">' + new Array(13).join('<i></i>') + '</div></div>' +
    '<p class="radio-station"></p>' +
    '<p class="radio-now" aria-live="polite"></p>' +
    '<div class="radio-dial" aria-hidden="true"><span class="radio-needle"></span></div>' +
    '</div>' +
    '<div class="radio-presets" role="group" aria-label="Presets">' + presets + '</div>' +
    '<div class="radio-controls">' +
    '<button type="button" class="radio-prev" aria-label="Previous station">◀◀</button>' +
    '<button type="button" class="radio-play" aria-label="Play">▶</button>' +
    '<button type="button" class="radio-next" aria-label="Next station">▶▶</button>' +
    '<label class="radio-vol"><span class="sr-only">Volume</span><input type="range" min="0" max="1" step="0.05"></label>' +
    '</div>' +
    '<p class="radio-credit">Now streaming <a class="radio-src" target="_blank" rel="noopener"></a>. Stations are independent and not affiliated with this site.</p>' +
    '</div>';
  document.body.appendChild(btn);
  document.body.appendChild(win);

  var $ = function (s) { return win.querySelector(s); };
  var playBtn = $('.radio-play'), vol = $('.radio-vol input');
  var audio = null, playing = false, metaTimer = null, ctx = null, noiseGain = null, tuneToken = 0;
  vol.value = state.vol;

  function st() { return STATIONS[state.i]; }
  function render() {
    var s = st();
    $('.radio-freq').textContent = s.freq;
    $('.radio-station').textContent = s.name;
    var a = $('.radio-src');
    a.textContent = s.src;
    a.href = s.site;
    $('.radio-needle').style.left = ((parseFloat(s.freq) - 87.5) / 21 * 100) + '%';
    Array.prototype.forEach.call(win.querySelectorAll('.radio-preset'), function (b, i) {
      b.classList.toggle('on', i === state.i);
      b.setAttribute('aria-pressed', String(i === state.i));
    });
    win.classList.toggle('on', playing);
    btn.classList.toggle('on', playing);
    $('.radio-air').textContent = playing ? 'On air' : 'Off air';
    playBtn.textContent = playing ? '❚❚' : '▶';
    playBtn.setAttribute('aria-label', playing ? 'Pause' : 'Play');
    if (!playing) setNow(s.tag);
  }
  function setNow(text) { $('.radio-now').textContent = text; }

  // Short burst of radio static between stations, generated in the browser.
  function staticBurst(ms) {
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === 'suspended') ctx.resume();
      var len = Math.floor(ctx.sampleRate * ms / 1000);
      var buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
      for (var i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (0.6 + 0.4 * Math.sin(i / 900));
      var src = ctx.createBufferSource();
      src.buffer = buf;
      var band = ctx.createBiquadFilter();
      band.type = 'bandpass';
      band.frequency.value = 1800;
      band.Q.value = 0.6;
      noiseGain = ctx.createGain();
      noiseGain.gain.value = 0.18 * state.vol;
      noiseGain.gain.setTargetAtTime(0, ctx.currentTime + ms / 1000 * 0.7, 0.05);
      src.connect(band).connect(noiseGain).connect(ctx.destination);
      src.start();
    } catch (e) {}
  }

  function fetchMeta() {
    var s = st(), m = s.meta, i = state.i;
    if (!m) { setNow(s.tag); return; }
    var url = m[0] === 'fip' ? 'https://api.radiofrance.fr/livemeta/pull/' + m[1]
      : m[0] === 'nts' ? 'https://www.nts.live/api/v2/live'
      : 'https://api.kexp.org/v2/plays/?limit=1';
    fetch(url).then(function (r) { return r.json(); }).then(function (d) {
      if (!playing || state.i !== i) return;
      var text = '';
      if (m[0] === 'fip') {
        var now = Date.now() / 1000;
        Object.keys(d.steps || {}).forEach(function (k) {
          var x = d.steps[k];
          if (x.embedType === 'song' && x.start <= now && now <= x.end) text = (x.authors || x.performers || '') + ' – ' + x.title;
        });
      } else if (m[0] === 'nts') {
        var ch = (d.results || [])[m[1]];
        if (ch) text = ch.now.broadcast_title;
      } else {
        var p = (d.results || [])[0];
        if (p && p.play_type === 'trackplay') text = p.artist + ' – ' + p.song;
      }
      setNow(text ? '♪ ' + text : s.tag);
    }).catch(function () { setNow(s.tag); });
  }

  function stop() {
    playing = false;
    tuneToken++;
    if (audio) { audio.pause(); audio.removeAttribute('src'); audio.load(); }
    clearInterval(metaTimer);
    render();
  }
  function play(withStatic) {
    if (!audio) {
      audio = new Audio();
      audio.preload = 'none';
      audio.addEventListener('playing', function () { if (playing) fetchMeta(); });
      audio.addEventListener('error', function () {
        if (playing && audio.getAttribute('src')) { stop(); setNow('Signal lost. Try another station.'); }
      });
    }
    playing = true;
    var token = ++tuneToken;
    render();
    setNow('Tuning in…');
    if (withStatic) staticBurst(450);
    setTimeout(function () {
      if (token !== tuneToken) return;
      audio.src = st().url;
      audio.volume = state.vol;
      audio.play().catch(function (e) {
        if (token === tuneToken && e && e.name === 'NotAllowedError') stop();
      });
    }, withStatic ? 380 : 0);
    clearInterval(metaTimer);
    metaTimer = setInterval(fetchMeta, 30000);
  }
  function tuneTo(i) {
    state.i = (i + STATIONS.length) % STATIONS.length;
    save();
    if (playing) play(true); else { staticBurst(250); render(); }
  }
  function open(show) {
    win.hidden = !show;
    btn.setAttribute('aria-expanded', String(show));
    state.open = show;
    save();
  }

  btn.addEventListener('click', function () { open(win.hidden); if (!win.hidden) playBtn.focus(); });
  $('.radio-x').addEventListener('click', function () { open(false); btn.focus(); });
  playBtn.addEventListener('click', function () { playing ? stop() : play(false); });
  $('.radio-prev').addEventListener('click', function () { tuneTo(state.i - 1); });
  $('.radio-next').addEventListener('click', function () { tuneTo(state.i + 1); });
  $('.radio-presets').addEventListener('click', function (e) {
    var b = e.target.closest('.radio-preset');
    if (b && +b.dataset.i !== state.i) tuneTo(+b.dataset.i);
  });
  vol.addEventListener('input', function () {
    state.vol = +vol.value;
    if (audio) audio.volume = state.vol;
    save();
  });
  win.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { open(false); btn.focus(); }
    else if (e.target.type !== 'range' && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
      e.preventDefault();
      tuneTo(state.i + (e.key === 'ArrowRight' ? 1 : -1));
    }
  });

  render();
  if (state.open) open(true);
})();

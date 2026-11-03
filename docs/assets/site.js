// Real visitor counter for the footer, powered by GoatCounter's public counter.
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

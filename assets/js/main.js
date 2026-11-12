(function () {
  var root = document.querySelector('[data-carousel]');
  if (!root) return;
  var slides = [].slice.call(root.querySelectorAll('.slide'));
  var dots = [].slice.call(root.querySelectorAll('.dot'));
  var delay = parseInt(root.dataset.interval, 10) || 6000;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var i = 0, timer;

  function show(n) {
    i = (n + slides.length) % slides.length;
    slides.forEach(function (s, k) { s.classList.toggle('active', k === i); });
    dots.forEach(function (d, k) { d.classList.toggle('active', k === i); });
  }
  function stop() { clearInterval(timer); }
  function start() {
    if (reduce || slides.length < 2) return;
    stop();
    timer = setInterval(function () { show(i + 1); }, delay);
  }

  root.querySelector('.prev').addEventListener('click', function () { show(i - 1); start(); });
  root.querySelector('.next').addEventListener('click', function () { show(i + 1); start(); });
  dots.forEach(function (d, k) { d.addEventListener('click', function () { show(k); start(); }); });
  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', start);
  root.addEventListener('focusin', stop);
  root.addEventListener('focusout', start);
  start();
})();

(function () {
  var list = document.getElementById('pub-list');
  if (!list) return;
  var items = [].slice.call(list.querySelectorAll('.pub'));
  var q = document.getElementById('pub-q'), y = document.getElementById('pub-year'),
      t = document.getElementById('pub-type'), n = document.getElementById('pub-n'),
      empty = document.getElementById('pub-empty');
  function apply() {
    var term = q.value.trim().toLowerCase(), c = 0;
    items.forEach(function (el) {
      var ok = (!term || el.dataset.q.indexOf(term) > -1) &&
               (!y.value || el.dataset.ano === y.value) &&
               (!t.value || el.dataset.tipo === t.value);
      el.hidden = !ok;
      if (ok) c++;
    });
    n.textContent = c;
    empty.hidden = c > 0;
  }
  ['input', 'change'].forEach(function (e) {
    q.addEventListener(e, apply); y.addEventListener(e, apply); t.addEventListener(e, apply);
  });
  apply();
})();
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
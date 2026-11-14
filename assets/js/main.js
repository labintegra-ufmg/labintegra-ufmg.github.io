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
    dots.forEach(function (d, k) { d.classList.toggle('active', k === i); if (k === i) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current'); });
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

/* PDI-CITAR */
;(function(){
  var en=(document.documentElement.lang||'').indexOf('en')===0;
  var T=en?{cite:'Cite',tit:'Cite (BibTeX)',copy:'Copy',copied:'Copied',load:'Loading…',err:'BibTeX unavailable',close:'Close'}
          :{cite:'Citar',tit:'Citar (BibTeX)',copy:'Copiar',copied:'Copiado',load:'Carregando…',err:'BibTeX indisponível',close:'Fechar'};
  document.querySelectorAll('img[src*="/images/pubs/"]').forEach(function(img){
    if(img.getAttribute('alt')) return;
    var n=img.parentElement,h=null;
    for(var k=0;n&&k<6&&!h;k++,n=n.parentElement){
      if(n.querySelectorAll('img[src*="/images/pubs/"]').length>1) break;
      h=n.querySelector('h2,h3,h4');
    }
    if(h) img.setAttribute('alt',h.textContent.trim());
  });
  var dlg=null,pre,cp,cache={};
  function build(){
    dlg=document.createElement('dialog'); dlg.className='cite-dlg'; dlg.setAttribute('aria-label',T.tit);
    var h=document.createElement('div'); h.className='cd-h';
    var s=document.createElement('strong'); s.textContent=T.tit;
    var x=document.createElement('button'); x.type='button'; x.className='cd-x'; x.setAttribute('aria-label',T.close); x.textContent='×';
    h.appendChild(s); h.appendChild(x);
    pre=document.createElement('pre'); pre.className='cd-b';
    var f=document.createElement('div'); f.className='cd-f';
    cp=document.createElement('button'); cp.type='button'; cp.className='cd-c'; cp.textContent=T.copy;
    f.appendChild(cp);
    dlg.appendChild(h); dlg.appendChild(pre); dlg.appendChild(f);
    document.body.appendChild(dlg);
    x.addEventListener('click',function(){dlg.close();});
    dlg.addEventListener('click',function(e){if(e.target===dlg) dlg.close();});
    cp.addEventListener('click',function(){
      var done=function(){cp.textContent=T.copied; setTimeout(function(){cp.textContent=T.copy},1500);};
      if(navigator.clipboard) navigator.clipboard.writeText(pre.textContent).then(done);
      else{var r=document.createRange(); r.selectNodeContents(pre); var q=getSelection(); q.removeAllRanges(); q.addRange(r); document.execCommand('copy'); done();}
    });
  }
  function abrir(doi){
    if(!dlg) build();
    cp.textContent=T.copy;
    if(cache[doi]){pre.textContent=cache[doi]; cp.disabled=false;}
    else{
      pre.textContent=T.load; cp.disabled=true;
      fetch('https://api.crossref.org/works/'+encodeURI(doi)+'/transform/application/x-bibtex')
        .then(function(r){if(!r.ok) throw 0; return r.text();})
        .then(function(b){cache[doi]=b.trim(); pre.textContent=cache[doi]; cp.disabled=false;})
        .catch(function(){pre.textContent=T.err;});
    }
    if(dlg.showModal) dlg.showModal(); else dlg.setAttribute('open','');
  }
  document.querySelectorAll('a[href*="doi.org/"]').forEach(function(a){
    if(a.closest('nav,header,footer')||a.dataset.cite) return;
    var m=a.href.match(/doi\.org\/(10\.[^?#]+)/i); if(!m) return;
    var doi=decodeURIComponent(m[1]); a.dataset.cite='1';
    var b=document.createElement('button'); b.type='button'; b.className='btn-cite';
    b.textContent=T.cite; b.title=T.tit; b.setAttribute('aria-label',T.tit); b.setAttribute('aria-haspopup','dialog');
    a.insertAdjacentElement('afterend',b);
    b.addEventListener('click',function(){abrir(doi);});
  });
})();

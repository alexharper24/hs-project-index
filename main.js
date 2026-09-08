/* Site Portfolio — filter, count, copy-path. No dependencies. */

(function () {
  const q = document.getElementById('q');
  const onlyTodo = document.getElementById('onlyTodo');
  const countEl = document.getElementById('count');
  const emptyEl = document.getElementById('empty');
  const grid = document.getElementById('grid');
  const cards = [...document.querySelectorAll('.wcard')];

  function apply() {
    const term = (q.value || '').trim().toLowerCase();
    const todoOnly = onlyTodo.checked;
    let shown = 0;
    cards.forEach(c => {
      const ok = (!term || c.dataset.hay.includes(term)) &&
                 (!todoOnly || Number(c.dataset.todo) > 0);
      c.classList.toggle('hide', !ok);
      if (ok) shown++;
    });
    countEl.textContent = shown === cards.length
      ? `${cards.length} sites`
      : `${shown} of ${cards.length}`;
    emptyEl.hidden = shown !== 0;
    grid.hidden = shown === 0;
  }

  q.addEventListener('input', apply);
  onlyTodo.addEventListener('change', apply);

  // "/" focuses the filter, Escape clears it
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.value = ''; apply(); q.blur(); }
  });

  // Copy the local path. The clipboard API needs a secure context; localhost
  // counts, but fall back to a hidden textarea for file:// just in case.
  document.querySelectorAll('.copy').forEach(btn => {
    const label = btn.querySelector('span');
    btn.addEventListener('click', async () => {
      let ok = false;
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        ok = true;
      } catch (_) {
        const ta = document.createElement('textarea');
        ta.value = btn.dataset.copy;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)';
        document.body.appendChild(ta);
        ta.select();
        try { ok = document.execCommand('copy'); } catch (__) { ok = false; }
        ta.remove();
      }
      const first = btn.firstChild;
      const original = first.textContent;
      first.textContent = ok ? 'Copied ' : 'Copy failed ';
      if (label) label.textContent = ok ? '✓' : '✗';
      btn.classList.toggle('copied', ok);
      setTimeout(() => {
        first.textContent = original;
        if (label) label.textContent = '→';
        btn.classList.remove('copied');
      }, 1400);
    });
  });

  apply();
})();

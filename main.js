/* Project Index — filter and copy-path. No dependencies. */

(function () {
  const q = document.getElementById('q');
  const onlyTodo = document.getElementById('onlyTodo');
  const cards = [...document.querySelectorAll('.card')];
  const cats = [...document.querySelectorAll('.cat')];

  function apply() {
    const term = (q.value || '').trim().toLowerCase();
    const todoOnly = onlyTodo.checked;
    cards.forEach(c => {
      const matchTerm = !term || c.dataset.hay.includes(term);
      const matchTodo = !todoOnly || Number(c.dataset.todo) > 0;
      c.classList.toggle('hide', !(matchTerm && matchTodo));
    });
    // hide a category heading once every card under it is filtered out
    cats.forEach(sec => {
      const any = [...sec.querySelectorAll('.card')].some(c => !c.classList.contains('hide'));
      sec.classList.toggle('hide', !any);
    });
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
    btn.addEventListener('click', async () => {
      const text = btn.dataset.copy;
      let ok = false;
      try {
        await navigator.clipboard.writeText(text);
        ok = true;
      } catch (_) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:absolute;left:-9999px';
        document.body.appendChild(ta);
        ta.select();
        try { ok = document.execCommand('copy'); } catch (__) { ok = false; }
        ta.remove();
      }
      const original = btn.textContent;
      btn.textContent = ok ? 'Copied' : 'Copy failed';
      btn.classList.toggle('copied', ok);
      setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove('copied');
      }, 1400);
    });
  });

  apply();
})();

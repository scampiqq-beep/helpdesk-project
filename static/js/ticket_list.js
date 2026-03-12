/* ticket_list.js — раскрывающиеся фильтры + AJAX фильтрация (настройки сохраняются на сервере) */
(function () {
  // Храним только значения фильтра (НЕ состояние открытия панели)
  // Требование: фильтр по умолчанию скрыт всегда, даже при возврате на страницу.
  const KEY = 'hd_ticket_filters_values_v1';
  const PREFS_KEY = 'hd_ticket_list_ui_v2';

  const toggleBtn = document.getElementById('filterToggle');
  const panel = document.getElementById('filterPanel');
  const form = document.getElementById('filterForm');
  const container = document.getElementById('ticketListContainer');
  const content = document.getElementById('ticketsContent');
  const loading = document.getElementById('ticketListLoading');
  const clearBtn = document.getElementById('clearFilters');



  const compactBtn = document.getElementById('compactToggle');

  // Sorting/grouping removed by requirements

  const applyCompact = () => {
    const on = (content?.dataset.compact || '0') === '1';
    // Важно: контент списка (ticketsContent) не меняется при AJAX (меняется только innerHTML),
    // поэтому класс компактности держим на wrapper'е, чтобы он не "слетал".
    if (content) content.classList.toggle('ticketlist-compact', on);
    if (compactBtn) compactBtn.classList.toggle('is-on', on);
  };

  const applySortUI = () => {};
  const buildParamsWithPrefs = (base) => ({ ...(base || {}) });
  if (!toggleBtn || !panel || !form || !container || !content) return;

  // --- helpers
  const readForm = () => {
    const fd = new FormData(form);
    const obj = {};
    for (const [k, v] of fd.entries()) {
      const val = (v ?? '').toString().trim();
      if (val === '') continue;
      if (Object.prototype.hasOwnProperty.call(obj, k)) {
        // multi-values (e.g. multi-select)
        if (Array.isArray(obj[k])) obj[k].push(val);
        else obj[k] = [obj[k], val];
      } else {
        obj[k] = val;
      }
    }
    return obj;
  };

  const writeForm = (obj) => {
    for (const el of form.elements) {
      if (!el.name) continue;
      if (!Object.prototype.hasOwnProperty.call(obj, el.name)) continue;

      const v = obj[el.name];

      if (el.type === 'checkbox') {
        // Для чекбоксов: считаем, что наличие ключа в obj => должен быть checked
        // (FormData не сохраняет unchecked)
        const want = Array.isArray(v) ? v.includes(el.value) : (v === el.value || v === '1' || v === true);
        el.checked = !!want;
        continue;
      }

      if (el.type === 'radio') {
        el.checked = (el.value === v);
        continue;
      }

      if (el.tagName === 'SELECT' && el.multiple) {
        const arr = Array.isArray(v) ? v : [v];
        for (const opt of el.options) {
          opt.selected = arr.includes(opt.value);
        }
      } else {
        el.value = v;
      }
    }
  };

  // Настройки фильтров/сортировки/показа храним на сервере (UserUIState).
  // Здесь не сохраняем значения в localStorage, чтобы избежать рассинхронизации.
  const saveValues = () => {};
  const loadState = () => null;

  const readPrefs = () => {
    try { return JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') || {}; } catch (_) { return {}; }
  };
  const writePrefs = (patch) => {
    try {
      const next = { ...readPrefs(), ...(patch || {}) };
      localStorage.setItem(PREFS_KEY, JSON.stringify(next));
      return next;
    } catch (_) { return patch || {}; }
  };

  const setPanelOpen = (open, animate = true) => {
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    panel.setAttribute('aria-hidden', open ? 'false' : 'true');

    if (open) {
      panel.classList.add('is-open');
      // анимация через max-height
      if (animate) {
        panel.style.maxHeight = '0px';
        // next frame
        requestAnimationFrame(() => {
          panel.style.maxHeight = panel.scrollHeight + 'px';
        });
      } else {
        panel.style.maxHeight = 'none';
      }
    } else {
      if (animate) {
        panel.style.maxHeight = panel.scrollHeight + 'px';
        requestAnimationFrame(() => {
          panel.style.maxHeight = '0px';
        });
      } else {
        panel.style.maxHeight = '0px';
      }
      panel.classList.remove('is-open');
    }

    // После открытия снимаем ограничение max-height, чтобы контент мог "перестраиваться"
    // (иначе при переносе кнопок может обрезать содержимое из-за overflow:hidden).
    const onEnd = () => {
      panel.removeEventListener('transitionend', onEnd);
      const isOpen = toggleBtn.getAttribute('aria-expanded') === 'true';
      if (isOpen) panel.style.maxHeight = 'none';
    };
    if (open && animate) {
      panel.addEventListener('transitionend', onEnd);
    }
    // Не сохраняем open/close состояние
  };

  // --- init: restore values ONLY if URL has no params
  const hasQuery = window.location.search && window.location.search.length > 1;
  const saved = loadState();
  const savedPrefs = readPrefs();

  if (!hasQuery && saved && saved.values) {
    writeForm(saved.values);
  }
  if (content && typeof savedPrefs.compact !== 'undefined') {
    content.dataset.compact = savedPrefs.compact ? '1' : '0';
  }
  if (!hasQuery && savedPrefs.show && form.querySelector('input[name="show"]')) {
    form.querySelector('input[name="show"]').value = String(savedPrefs.show);
  }
  // Фильтр всегда закрыт по умолчанию
  setPanelOpen(false, false);
  applyCompact();

  const savePrefs = async (payload) => {
    try {
      await fetch('/api/ui/ticket-list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify(payload || {})
      });
    } catch (_) {}
  };

  if (compactBtn) {
    compactBtn.addEventListener('click', () => {
      const on = (content?.dataset.compact || '0') === '1';
      const next = on ? '0' : '1';
      if (content) content.dataset.compact = next;
      applyCompact();
      writePrefs({ compact: next === '1' });
      savePrefs({ compact: next === '1' });
    });
  }

  toggleBtn.addEventListener('click', () => {
    const open = toggleBtn.getAttribute('aria-expanded') === 'true';
    setPanelOpen(!open, true);
  });

  // Keep panel height correct on resize (when open)
  window.addEventListener('resize', () => {
    const open = toggleBtn.getAttribute('aria-expanded') === 'true';
    if (open) panel.style.maxHeight = panel.scrollHeight + 'px';
  });

  // --- AJAX load
  let inflight = null;
  const setLoading = (on) => {
    if (!loading) return;
    loading.classList.toggle('is-on', !!on);
    loading.setAttribute('aria-hidden', on ? 'false' : 'true');
  };

  const fetchList = async (paramsObj, pushUrl = true, collapseAfter = false) => {
    const usp = new URLSearchParams();
    Object.entries(paramsObj || {}).forEach(([k, v]) => {
      if (Array.isArray(v)) {
        v.forEach(it => {
          const val = (it ?? '').toString();
          if (val !== '') usp.append(k, val);
        });
      } else {
        const val = (v ?? '').toString();
        if (val !== '') usp.set(k, val);
      }
    });
    const qs = usp.toString();
    const url = '/tickets' + (qs ? ('?' + qs) : '');
    const ajaxUrl = url + (qs ? '&ajax=1' : '?ajax=1');

    if (pushUrl) {
      window.history.replaceState({}, '', url);
    }

    saveValues();

    try {
      if (inflight) inflight.abort();
      inflight = new AbortController();

      setLoading(true);

      const res = await fetch(ajaxUrl, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: inflight.signal
      });

      if (!res.ok) return false;
      const data = await res.json();
      if (data && data.success && typeof data.html === 'string') {
        content.innerHTML = data.html;
        applyCompact();
        applySortUI();
        if (window.HDSlaTimers && typeof window.HDSlaTimers.refresh === 'function') window.HDSlaTimers.refresh(content);
        // preview/presence removed
        if (collapseAfter) {
          setPanelOpen(false, true);
        }
        return true;
      }
      return false;
    } catch (_) {
      // ignore
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Preview + Presence removed


  // Pagination (AJAX): перехватываем клики по ссылкам пагинации в списке
  container.addEventListener('click', (e) => {
    // Copy ticket link (quick action)
    const showLink = e.target.closest && e.target.closest('a[data-show]');
    if (showLink) {
      const showValue = parseInt(showLink.getAttribute('data-show') || '', 10);
      if ([10,25,50].includes(showValue)) {
        writePrefs({ show: showValue, compact: (content?.dataset.compact || '0') === '1' });
        savePrefs({ show: showValue, compact: (content?.dataset.compact || '0') === '1' });
      }
    }

    const copyBtn = e.target.closest && e.target.closest('button.js-copy-ticket');
    if (copyBtn) {
      e.preventDefault();
      const rel = copyBtn.getAttribute('data-url') || '';
      const url = rel ? (new URL(rel, window.location.origin)).toString() : '';
      if (!url) return;

      const doCopy = async () => {
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(url);
          } else {
            const ta = document.createElement("textarea");
            ta.value = url;
            ta.style.position = "fixed";
            ta.style.left = "-9999px";
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            ta.remove();
          }
          if (window.HDUI && typeof window.HDUI.toast === "function") {
            window.HDUI.toast("Ссылка скопирована", "success");
          }
        } catch (_) {
          if (window.HDUI && typeof window.HDUI.toast === "function") {
            window.HDUI.toast("Не удалось скопировать", "danger");
          } else {
            try { alert("Не удалось скопировать"); } catch (e) {}
          }
        }
      };

      doCopy();
      return;
    }

    // Bitrix-like: show (10/25/50)
    const showA = e.target.closest && e.target.closest('a.bx-link[data-show]');
    if (showA) {
      e.preventDefault();
      const n = showA.getAttribute('data-show');
      writePrefs({ show: Number(n), compact: (content?.dataset.compact || '0') === '1' });
      const params = readForm();
      params.show = n;
      const showInput = form.querySelector('input[name="show"]');
      if (showInput) showInput.value = n;
      delete params.page;
      fetchList(buildParamsWithPrefs(params), true, false);
      return;
    }

    // Sorting: как в Bitrix — обычная навигация по ссылке (без AJAX перехвата)
    // Это гарантирует работу сортировки даже при любых проблемах с JS/AJAX.

    // Pagination (AJAX)

    // Supports both legacy boxed pager (.page-link) and Bitrix-like plain pager (.bx-page-link/.bx-next)
    const a = e.target.closest && e.target.closest('a.page-link[data-page], a.bx-page-link[data-page], a.bx-next[data-page]');
    if (!a) return;
    const disabled = a.classList.contains('is-disabled') || a.classList.contains('bx-page-disabled') || a.getAttribute('aria-disabled') === 'true';
    if (disabled) {
      e.preventDefault();
      return;
    }
    const page = a.getAttribute('data-page');
    if (!page) return;
    e.preventDefault();

    const href = a.getAttribute('href') || '';

    // ВАЖНО: для пагинации берём параметры из href,
    // потому что readForm() может не содержать sort/dir/show и части фильтров,
    // а href уже сформирован сервером с учётом текущего состояния списка.
    let params = {};
    try {
      const u = new URL(a.getAttribute('href') || '', window.location.origin);
      const usp = u.searchParams;
      for (const key of new Set(Array.from(usp.keys()))) {
        const vals = usp.getAll(key);
        params[key] = (vals.length > 1) ? vals : (vals[0] ?? '');
      }
      // На всякий случай принудительно выставим page из data-page
      params.page = page;
    } catch (_) {
      params = readForm();
      params.page = page;
    }

    Promise.resolve(fetchList(buildParamsWithPrefs(params), true, false)).then((ok) => {
      if (!ok && href) window.location.href = href;
    });
    // при переходе по страницам фильтр не трогаем (не сворачиваем/разворачиваем)
  });


  form.addEventListener('submit', (e) => {
    e.preventDefault();
    saveValues();
    const p = readForm();
    delete p.page;
    fetchList(buildParamsWithPrefs(p), true, true);
  });

  // optional: live debounce on select changes
  let t = null;
  form.addEventListener('change', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      saveValues();
      fetchList(buildParamsWithPrefs(readForm()), true, false);
    }, 150);
  });

  // If we восстановили значения из localStorage и URL пустой — сразу подгрузим список
  if (!hasQuery && ((saved && saved.values && Object.keys(saved.values).length) || savedPrefs.show)) {
    fetchList(buildParamsWithPrefs(readForm()), true, false);
  }

  // Clear filters: wipe form + localStorage + URL + reload list
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      form.reset();
      // Close filter panel after clear
      setPanelOpen(false, true);
      try { localStorage.removeItem(PREFS_KEY); } catch (_) {}
      if (content) content.dataset.compact = '0';
      applyCompact();
      // clear=1 сбрасывает сохранённые настройки на сервере
      fetchList({ clear: '1' }, true, false);
    });
  }

  // Sorting/grouping removed

  applySortUI();
  if (window.HDSlaTimers && typeof window.HDSlaTimers.init === 'function') window.HDSlaTimers.init(content);
  // preview/presence removed
})();

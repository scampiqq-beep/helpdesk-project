(function () {
  const script = document.currentScript;
  // В некоторых сборках/браузерах document.currentScript может быть null.
  // Поэтому берём ticketId из нескольких источников.
  const ticketId = script?.dataset?.ticketId
    || document.getElementById('presenceCard')?.dataset?.ticketId
    || window.TICKET_ID;
  if (!ticketId) return;

  const elLoading = document.getElementById('presenceLoading');
  const elList = document.getElementById('presenceList');
  const elCount = document.getElementById('presenceCount');

  function initials(name) {
    const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '?';
    const a = parts[0][0] || '';
    const b = parts.length > 1 ? (parts[1][0] || '') : '';
    return (a + b).toUpperCase();
  }

  function roleLabel(role) {
    if (role === 'admin') return 'Админ';
    if (role === 'operator') return 'Оператор';
    if (role === 'client') return 'Клиент';
    return role || '';
  }

  function render(viewers) {
    const list = Array.isArray(viewers) ? viewers : [];
    if (elCount) elCount.textContent = list.length ? `${list.length} онлайн` : '—';

    if (!elList) return;
    if (!list.length) {
      elList.style.display = 'block';
      elList.innerHTML = '<div class="text-muted small">Сейчас никто не просматривает заявку</div>';
      if (elLoading) elLoading.style.display = 'none';
      return;
    }

    elList.style.display = 'flex';
    elList.innerHTML = list.map(v => {
      const dn = v.display_name || '—';
      const rl = roleLabel(v.role);
      return `
        <div class="presence-user">
          <div class="presence-dot" aria-hidden="true"></div>
          <div class="presence-avatar" aria-hidden="true">${initials(dn)}</div>
          <div class="presence-meta">
            <div class="presence-name">${escapeHtml(dn)}</div>
            <div class="presence-role">${escapeHtml(rl)}</div>
          </div>
        </div>
      `;
    }).join('');

    if (elLoading) elLoading.style.display = 'none';
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  async function heartbeat() {
    try {
      await fetch(`/api/ticket/${ticketId}/presence/heartbeat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_typing: false })
      });
    } catch (e) {
      // ignore
    }
  }

  async function pollOnce() {
    try {
      const r = await fetch(`/api/ticket/${ticketId}/presence`, { method: 'GET' });
      const data = await r.json();
      if (data && data.success) render(data.viewers);
    } catch (e) {
      // ignore
    }
  }

  function startStream() {
    const es = new EventSource(`/api/ticket/${ticketId}/presence/stream`);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data && data.success) {
          render(data.viewers);
        }
      } catch (e) {
        // ignore
      }
    };
    es.onerror = () => {
      // Stream may be interrupted by proxy/browser; try reconnect.
      es.close();
      // fallback: если SSE недоступен, периодически опрашиваем.
      pollOnce();
      setTimeout(startStream, 3000);
    };
  }

  // initial
  heartbeat();
  setInterval(heartbeat, 8000);
  pollOnce();
  startStream();
})();

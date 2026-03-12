(function(){
  const script = document.currentScript;
  const ticketId = script?.dataset?.ticketId;
  if(!ticketId) return;

  const fab = document.getElementById('opChatFab');
  const panel = document.getElementById('opChatPanel');
  const btnClose = document.getElementById('opChatClose');
  const box = document.getElementById('opChatMessages');
  const form = document.getElementById('opChatForm');
  const input = document.getElementById('opChatText');
  const badge = document.getElementById('opChatBadge');
  const lockedNote = document.getElementById('opChatLockedNote');

  if(!fab || !panel || !box || !form || !input) return;

  let stream = null;
  let lastId = 0;
  let ticketClosed = false;
  let unread = 0;

  function esc(s){
    return String(s)
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }

  function scrollToBottom(){
    box.scrollTop = box.scrollHeight;
  }

  function renderMessage(m){
    const mine = (Number(m.user_id) === Number(window.CURRENT_USER_ID || 0));
    const wrap = document.createElement('div');
    wrap.className = 'opchat-row ' + (mine ? 'mine' : 'theirs');
    wrap.innerHTML = `
      <div class="opchat-bubble">
        <div class="opchat-author">${esc(m.author || '')}</div>
        <div class="opchat-text">${esc(m.message || '')}</div>
        <div class="opchat-time">${esc(m.created_at || '')}</div>
      </div>
    `;
    box.appendChild(wrap);
  }

  function setBadge(n){
    unread = n;
    if(!badge) return;
    if(!n || n <= 0){
      badge.hidden = true;
      badge.textContent = '';
      return;
    }
    badge.hidden = false;
    badge.textContent = String(Math.min(n, 99));
  }

  async function markRead(){
    if(!lastId) { setBadge(0); return; }
    try{
      await fetch(`/api/ticket/${ticketId}/opchat/mark-read`, {
        method:'POST',
        credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},
        body: JSON.stringify({ last_id: lastId })
      });
    }catch(e){}
    setBadge(0);
    // notify global badge updater
    try{ window.dispatchEvent(new CustomEvent('opchat:read', {detail:{ticketId:ticketId}})); }catch(e){}
  }

  async function loadHistory(){
    box.innerHTML = '<div class="opchat-empty">Загрузка...</div>';
    try{
      const r = await fetch(`/api/ticket/${ticketId}/opchat/messages?limit=80`);
      const data = await r.json();
      if(!data.success){
        box.innerHTML = '<div class="opchat-empty">Нет доступа</div>';
        return;
      }
      ticketClosed = !!data.ticket_closed;
      box.innerHTML = '';
      const items = data.items || [];
      if(!items.length){
        box.innerHTML = '<div class="opchat-empty">Сообщений пока нет</div>';
      } else {
        items.forEach(renderMessage);
        lastId = items[items.length-1].id;
      }

      // on open chat, consider everything read
      setBadge(0);
      markRead();
      if(ticketClosed){
        input.disabled = true;
        input.placeholder = 'Тикет закрыт — чат только для чтения';
        if(lockedNote) lockedNote.hidden = false;
      } else {
        input.disabled = false;
        input.placeholder = 'Сообщение...';
        if(lockedNote) lockedNote.hidden = true;
      }
      scrollToBottom();
    }catch(e){
      box.innerHTML = '<div class="opchat-empty">Ошибка загрузки</div>';
    }
  }

  function startStream(){
    if(stream) stream.close();
    stream = new EventSource(`/api/ticket/${ticketId}/opchat/stream?after=${lastId}`);
    stream.onmessage = (ev)=>{
      try{
        const data = JSON.parse(ev.data);
        if(!data.success) return;
        ticketClosed = !!data.ticket_closed;
        const items = data.items || [];
        if(items.length){
          // remove empty placeholder
          const empty = box.querySelector('.opchat-empty');
          if(empty) empty.remove();
          items.forEach(renderMessage);
          lastId = data.last_id || items[items.length-1].id;
          // if panel hidden, count as unread; otherwise mark as read immediately
          if(panel.hidden){
            setBadge(unread + items.filter(m => Number(m.user_id) !== Number(window.CURRENT_USER_ID || 0)).length);
            try{ window.dispatchEvent(new CustomEvent('opchat:unread', {detail:{ticketId:ticketId}})); }catch(e){}
          }else{
            setBadge(0);
            markRead();
            scrollToBottom();
          }
        }
        if(ticketClosed){
          input.disabled = true;
          input.placeholder = 'Тикет закрыт — чат только для чтения';
          if(lockedNote) lockedNote.hidden = false;
        } else {
          if(lockedNote) lockedNote.hidden = true;
        }
      }catch(e){
        // ignore
      }
    };
    stream.onerror = ()=>{
      stream.close();
      setTimeout(startStream, 3000);
    };
  }

  async function send(text){
    try{
      const r = await fetch(`/api/ticket/${ticketId}/opchat/send`, {
        method:'POST',
        credentials:'same-origin',
        headers:{
          'Content-Type':'application/json',
          'X-Requested-With':'XMLHttpRequest'
        },
        body: JSON.stringify({message:text})
      });

      let data = null;
      try{ data = await r.json(); } catch(e){ data = {success:false, error:'bad_response'}; }

      if(!r.ok || !data || !data.success){
        const err = (data && data.error) ? data.error : (r.status ? String(r.status) : 'error');
        // show inline error
        const note = document.createElement('div');
        note.className = 'opchat-empty';
        note.textContent = (err === 'forbidden') ? 'Нет доступа к чату' :
                           (err === 'ticket_closed') ? 'Тикет закрыт — чат только для чтения' :
                           'Не удалось отправить сообщение';
        box.appendChild(note);
        scrollToBottom();

        if(err === 'ticket_closed'){
          ticketClosed = true;
          input.disabled = true;
          input.placeholder = 'Тикет закрыт — чат только для чтения';
          if(lockedNote) lockedNote.hidden = false;
        }
        return false;
      }
      return true;
    }catch(e){
      const note = document.createElement('div');
      note.className = 'opchat-empty';
      note.textContent = 'Сеть недоступна — сообщение не отправлено';
      box.appendChild(note);
      scrollToBottom();
      return false;
    }
  }

  function open(){
    panel.hidden = false;
    fab.classList.add('open');
    loadHistory().then(()=> startStream());
    setTimeout(()=> input.focus(), 50);
  }

  function close(){
    panel.hidden = true;
    fab.classList.remove('open');
    if(stream){ stream.close(); stream = null; }
  }

  fab.addEventListener('click', ()=>{
    if(panel.hidden) open(); else close();
  });
  btnClose?.addEventListener('click', close);

  document.addEventListener('keydown', (e)=>{
    if(e.key === 'Escape' && !panel.hidden) close();
  });

  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    if(ticketClosed) return;
    const text = input.value.trim();
    if(!text) return;
    input.value = '';
    await send(text);
    // after send, mark read (we are in chat)
    markRead();
  });

  // initial unread count for this ticket
  (async function seedUnread(){
    try{
      const r = await fetch(`/api/ticket/${ticketId}/opchat/unread-count`, {credentials:'same-origin'});
      const data = await r.json();
      if(data && data.success){ setBadge(Number(data.unread || 0)); }
    }catch(e){}
  })();

  // auto-open from bell/notifications page links
  try{
    const p = new URLSearchParams(window.location.search);
    if(p.get('open_opchat') === '1'){
      open();
    }
  }catch(e){}

})();

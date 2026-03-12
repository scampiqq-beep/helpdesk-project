// shared_departments.js
// Быстрое снятие доп. отдела без открытия модалки делегирования.

(function(){
  function qs(id){ return document.getElementById(id); }

  async function remove(ticketId, deptId, btnEl){
    try{
      if(btnEl) btnEl.disabled = true;

      const r = await fetch(`/api/ticket/${ticketId}/shared_departments/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ department_id: deptId })
      });

      if(!r.ok){
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }

      // Удаляем из DOM
      const item = btnEl && btnEl.closest('.shared-dept-item');
      if(item) item.remove();

      const list = qs('sharedDeptsList');
      const empty = qs('sharedDeptsEmpty');
      if(list && list.children.length === 0){
        if(empty) empty.style.display = '';
        else {
          const span = document.createElement('span');
          span.className = 'text-muted';
          span.id = 'sharedDeptsEmpty';
          span.textContent = '—';
          list.replaceWith(span);
        }
      }
    }catch(e){
      console.error(e);
      alert('Не удалось снять отдел: ' + (e && e.message ? e.message : e));
      if(btnEl) btnEl.disabled = false;
    }
  }

  window.HDSharedDepts = { remove };
})();

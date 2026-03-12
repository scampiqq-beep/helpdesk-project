/* ui.js — минимальная замена bootstrap.bundle (dropdown / modal / collapse).
   Работает с существующими data-bs-* атрибутами. */

(function () {
  const qs = (sel, root=document) => root.querySelector(sel);
  const qsa = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  // --- Collapse ---
  function toggleCollapse(target) {
    if (!target) return;
    target.classList.toggle('show');
  }

  function handleCollapseClick(e) {
    const btn = e.target.closest('[data-bs-toggle="collapse"]');
    if (!btn) return;
    e.preventDefault();
    const sel = btn.getAttribute('data-bs-target') || btn.getAttribute('href');
    const target = sel ? qs(sel) : null;
    toggleCollapse(target);
  }

  // --- Dropdown ---
  function closeAllDropdowns(exceptMenu=null) {
    qsa('.dropdown-menu.show').forEach(menu => {
      if (menu !== exceptMenu) menu.classList.remove('show');
    });
  }

  function handleDropdownClick(e) {
    const toggle = e.target.closest('[data-bs-toggle="dropdown"]');
    if (!toggle) return;
    e.preventDefault();
    const dd = toggle.closest('.dropdown') || toggle.parentElement;
    const menu = dd ? qs('.dropdown-menu', dd) : null;
    if (!menu) return;
    const willOpen = !menu.classList.contains('show');
    closeAllDropdowns();
    if (willOpen) menu.classList.add('show');
  }

  document.addEventListener('click', (e) => {
    // click outside closes dropdown
    if (!e.target.closest('.dropdown')) closeAllDropdowns();
  });

  // --- Modal ---
  let backdropEl = null;
  function ensureBackdrop() {
    if (backdropEl) return backdropEl;
    backdropEl = document.createElement('div');
    backdropEl.className = 'modal-backdrop';
    backdropEl.addEventListener('click', () => {
      const open = qs('.modal.show');
      if (open) hideModal(open);
    });
    return backdropEl;
  }

  function showModal(modal) {
    if (!modal) return;
    document.body.appendChild(ensureBackdrop());
    document.body.style.overflow = 'hidden';
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.classList.remove('show');
    modal.setAttribute('aria-hidden', 'true');
    // close backdrop if no modals
    if (!qs('.modal.show')) {
      if (backdropEl && backdropEl.parentNode) backdropEl.parentNode.removeChild(backdropEl);
      backdropEl = null;
      document.body.style.overflow = '';
    }
  }

  function handleModalClick(e) {
    const opener = e.target.closest('[data-bs-toggle="modal"]');
    if (opener) {
      e.preventDefault();
      const sel = opener.getAttribute('data-bs-target') || opener.getAttribute('href');
      const modal = sel ? qs(sel) : null;
      showModal(modal);
      return;
    }

    const dismiss = e.target.closest('[data-bs-dismiss="modal"], .btn-close');
    if (dismiss) {
      const modal = dismiss.closest('.modal');
      hideModal(modal);
      return;
    }

    // clicking on modal background closes (if clicked outside dialog)
    const modalBg = e.target.classList.contains('modal') ? e.target : null;
    if (modalBg && modalBg.classList.contains('show')) hideModal(modalBg);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const open = qs('.modal.show');
      if (open) hideModal(open);
      closeAllDropdowns();
    }
  });

  // --- Init ---
  document.addEventListener('click', (e) => {
    handleCollapseClick(e);
    handleDropdownClick(e);
    handleModalClick(e);
  });

  // Публичный мини-API для шаблонов (вместо bootstrap.Modal/Alert)
  window.HDUI = {
    showModalById(id) {
      const el = id ? qs('#' + id) : null;
      if (el) showModal(el);
    },
    hideModalById(id) {
      const el = id ? qs('#' + id) : null;
      if (el) hideModal(el);
    },
    closeAlert(el) {
      if (el && el.remove) el.remove();
    },
    toast(message, type='info'){
      try{
        let wrap = document.getElementById('hdToasts');
        if(!wrap){
          wrap = document.createElement('div');
          wrap.id = 'hdToasts';
          wrap.className = 'hd-toasts';
          document.body.appendChild(wrap);
        }
        const el = document.createElement('div');
        el.className = 'hd-toast hd-toast-' + type;
        el.innerHTML = `
          <div class="hd-toast-row">
            <div class="hd-toast-title">${String(message||'')}</div>
            <button class="hd-toast-x" type="button" aria-label="Закрыть">×</button>
          </div>`;
        wrap.appendChild(el);
        const kill = ()=>{ try{ el.remove(); }catch(e){} };
        el.querySelector('.hd-toast-x')?.addEventListener('click', kill);
        setTimeout(kill, 2200);
      }catch(e){}
    }
  };

  // Topbar: burger + user dropdown
  document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.getElementById('navToggle');
    const menu = document.getElementById('topbarMenu');
    if (navToggle && menu) {
      navToggle.addEventListener('click', () => {
        const open = menu.classList.toggle('is-open');
        navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    const userBtn = document.getElementById('userBtn');
    const userDd = document.getElementById('userDropdown');
    if (userBtn && userDd) {
      const close = () => {
        userDd.hidden = true;
        userBtn.setAttribute('aria-expanded', 'false');
      };
      userBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const willOpen = userDd.hidden;
        userDd.hidden = !willOpen;
        userBtn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      });
      document.addEventListener('click', (e) => {
        if (!e.target.closest('#userMenu')) close();
      });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
    }
  });
})();

(function(){
  function closeAll(except){
    document.querySelectorAll('.ms.open').forEach(ms=>{ if(ms!==except) ms.classList.remove('open'); });
  }

  function updateLabel(ms){
    const trigger = ms.querySelector('.ms-trigger');
    const checks = Array.from(ms.querySelectorAll('input[type="checkbox"]'));
    const selected = checks.filter(c=>c.checked);
    if(selected.length===0){
      trigger.textContent = 'Все';
      ms.classList.remove('has-value');
      return;
    }
    ms.classList.add('has-value');
    const labels = selected.slice(0,2).map(c=>{
      const span = c.parentElement.querySelector('span');
      return span ? span.textContent.trim() : c.value;
    });
    let text = labels.join(', ');
    if(selected.length>2) text += ` +${selected.length-2}`;
    trigger.textContent = text;
  }

  function init(ms){
    const trigger = ms.querySelector('.ms-trigger');
    if(!trigger) return;

    updateLabel(ms);

    trigger.addEventListener('click', (e)=>{
      e.preventDefault();
      const isOpen = ms.classList.contains('open');
      closeAll(ms);
      ms.classList.toggle('open', !isOpen);
    });

    ms.addEventListener('change', (e)=>{
      if(e.target && e.target.matches('input[type="checkbox"]')){
        updateLabel(ms);
      }
    });
  }

  document.addEventListener('click', (e)=>{
    const ms = e.target.closest && e.target.closest('.ms');
    if(!ms) closeAll(null);
  });

  document.addEventListener('keydown', (e)=>{
    if(e.key==='Escape') closeAll(null);
  });

  document.addEventListener('DOMContentLoaded', ()=>{
    document.querySelectorAll('.ms[data-ms]').forEach(init);
    // Update labels after form.reset() (Clear button in ticket_list.js calls form.reset())
    const form = document.getElementById('filterForm');
    if(form){
      form.addEventListener('reset', ()=>{
        setTimeout(()=>{
          document.querySelectorAll('.ms[data-ms]').forEach(updateLabel);
        }, 0);
      });
    }
  });
})();

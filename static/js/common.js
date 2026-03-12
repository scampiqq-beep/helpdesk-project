// Закрытие флеш-сообщений
document.addEventListener('DOMContentLoaded', function() {
    // Закрытие флеш-сообщений
    document.querySelectorAll('.flash-close').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.flash').remove();
        });
    });
    
    // Автоматическое скрытие флеш-сообщений через 5 секунд
    setTimeout(() => {
        document.querySelectorAll('.flash').forEach(flash => {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.5s';
            setTimeout(() => flash.remove(), 500);
        });
    }, 5000);
    
    // Мобильное меню (если нужно)
    if (window.innerWidth <= 768) {
        const menuToggle = document.createElement('button');
        menuToggle.className = 'btn btn-primary mobile-menu-toggle';
        menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        menuToggle.style.position = 'fixed';
        menuToggle.style.top = '1rem';
        menuToggle.style.left = '1rem';
        menuToggle.style.zIndex = '1001';
        
        menuToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('active');
        });
        
        document.body.appendChild(menuToggle);
    }
});
(function(){
    let slaTimerHandle = null;

    function formatCompactMinutes(totalMinutes){
        const sign = totalMinutes < 0 ? '-' : '';
        const minsAbs = Math.abs(totalMinutes);
        const days = Math.floor(minsAbs / 1440);
        const hours = Math.floor((minsAbs % 1440) / 60);
        const minutes = minsAbs % 60;
        if (days > 0) return sign + days + ' д' + (hours ? ' ' + hours + ' ч' : '');
        if (hours > 0) return sign + hours + ' ч';
        return sign + Math.max(1, minutes) + ' мин';
    }

    function stateFromDiff(diffMinutes, paused){
        if (paused) return 'paused';
        if (diffMinutes < 0) return 'overdue';
        if (diffMinutes <= 120) return 'warning';
        return 'ok';
    }

    function updateSlaElement(el){
        if (!el) return;
        const chip = el.querySelector('.sla-bitrix__chip');
        const paused = (el.dataset.paused || '0') === '1';
        const live = (el.dataset.live || '0') === '1';
        if (!live || paused) return;
        const raw = (el.dataset.deadlineIso || '').trim();
        if (!raw) return;
        const deadline = new Date(raw);
        if (Number.isNaN(deadline.getTime())) return;
        const diffMinutes = Math.floor((deadline.getTime() - Date.now()) / 60000);
        const state = stateFromDiff(diffMinutes, paused);
        el.dataset.state = state;
        if (chip){
            chip.textContent = formatCompactMinutes(diffMinutes);
            chip.classList.remove('sla-ok','sla-warning','sla-overdue','sla-paused','sla-normal');
            chip.classList.add('sla-' + state);
        }
    }

    function refreshSlaTimers(root){
        (root || document).querySelectorAll('.js-sla-live').forEach(updateSlaElement);
    }

    function initSlaTimers(root){
        refreshSlaTimers(root || document);
        if (slaTimerHandle) return;
        slaTimerHandle = window.setInterval(function(){ refreshSlaTimers(document); }, 60000);
    }

    window.HDSlaTimers = {
        init: initSlaTimers,
        refresh: refreshSlaTimers
    };

    document.addEventListener('DOMContentLoaded', function(){
        initSlaTimers(document);
    });
})();

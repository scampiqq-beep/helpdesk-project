function escapeHtml(value){
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function setBadgeCount(count){
    const badge = document.getElementById('notifBadge');
    if(!badge){ return; }
    const value = Number(count || 0);
    if(value > 0){
        badge.textContent = value > 99 ? '99+' : String(value);
        badge.classList.remove('hidden');
    } else {
        badge.textContent = '';
        badge.classList.add('hidden');
    }
}

function renderNotificationDropdown(data){
    const list = document.getElementById('notifList');
    if(!list){ return; }
    const notifications = Array.isArray(data.notifications) ? data.notifications : [];
    const opchatThreads = Array.isArray(data.opchat_threads) ? data.opchat_threads : [];
    const chunks = [];

    if(opchatThreads.length){
        chunks.push('<div class="notif-sep">Чат операторов</div>');
        for(const thread of opchatThreads){
            const ticketId = escapeHtml(thread.ticket_id);
            const unread = escapeHtml(thread.unread);
            const lastAuthor = escapeHtml(thread.last_author || 'Оператор');
            const lastMessage = escapeHtml(thread.last_message || '');
            const lastAt = escapeHtml(thread.last_at || '');
            chunks.push(`
                <a class="notif-item unread" href="/ticket/${ticketId}?open_opchat=1">
                    <div class="notif-text">Тикет #${ticketId} · ${lastAuthor} · ${unread} непрочит.</div>
                    ${lastMessage ? `<div class="notif-body">${lastMessage}</div>` : ''}
                    ${lastAt ? `<div class="notif-time">${lastAt}</div>` : ''}
                </a>
            `);
        }
    }

    if(notifications.length){
        if(opchatThreads.length){
            chunks.push('<div class="notif-sep">Уведомления</div>');
        }
        for(const item of notifications){
            const id = escapeHtml(item.id);
            const title = escapeHtml(item.title || 'Уведомление');
            const createdAt = escapeHtml(item.created_at || '');
            const itemClass = item.is_read ? 'notif-item' : 'notif-item unread';
            chunks.push(`
                <a class="${itemClass}" href="/n/${id}">
                    <div class="notif-text">${title}</div>
                    ${createdAt ? `<div class="notif-time">${createdAt}</div>` : ''}
                </a>
            `);
        }
    }

    if(!chunks.length){
        chunks.push('<div class="notif-empty">Нет уведомлений</div>');
    }

    list.innerHTML = chunks.join('');
}

async function refreshNotifications(){
    try{
        const countsResponse = await fetch('/api/ui/unread-counts', {credentials:'same-origin'});
        const countsData = await countsResponse.json();
        setBadgeCount(countsData.total || 0);
    }catch(e){}

    try{
        const itemsResponse = await fetch('/api/ui/dropdown-items', {credentials:'same-origin'});
        const itemsData = await itemsResponse.json();
        renderNotificationDropdown(itemsData || {});
    }catch(e){}
}

document.addEventListener('DOMContentLoaded', () => {
    const notifBtn = document.getElementById('notifBtn');
    if(notifBtn){
        notifBtn.addEventListener('click', () => {
            window.setTimeout(refreshNotifications, 0);
        });
    }
    window.addEventListener('opchat:unread', () => {
        window.setTimeout(refreshNotifications, 0);
    });
    refreshNotifications();
    window.setInterval(refreshNotifications, 15000);
});

document.addEventListener('DOMContentLoaded', function() {
    // Автоматическое скрытие через 5 секунд
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(message => {
        // Кнопка закрытия
        const closeBtn = message.querySelector('.flash-message-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                hideFlashMessage(message);
            });
        }
        
        // Автоскрытие через 5 секунд (кроме error)
        if (!message.classList.contains('flash-message-error')) {
            setTimeout(() => {
                hideFlashMessage(message);
            }, 5000);
        }
    });
    
    function hideFlashMessage(message) {
        message.classList.add('hiding');
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 300);
    }
    
    // Закрытие по клику вне сообщения (опционально)
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.flash-message')) {
            flashMessages.forEach(hideFlashMessage);
        }
    });
});
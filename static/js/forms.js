// forms.js - Общие функции для форм

// Инициализация переключателей видимости пароля
function initPasswordToggles() {
    document.querySelectorAll('.password-toggle-btn').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
}

// Валидация email
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Валидация формы
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Проверка email полей
            const emailInputs = this.querySelectorAll('input[type="email"]');
            emailInputs.forEach(input => {
                if (input.value && !validateEmail(input.value)) {
                    e.preventDefault();
                    alert('Пожалуйста, введите корректный email адрес');
                    input.focus();
                    return false;
                }
            });

            // Проверка совпадения паролей
            const passwordInput = this.querySelector('input[name="password"]');
            const confirmInput = this.querySelector('input[name="confirm_password"]') || 
                                this.querySelector('input[name="password2"]');
            
            if (passwordInput && confirmInput && 
                passwordInput.value && confirmInput.value && 
                passwordInput.value !== confirmInput.value) {
                e.preventDefault();
                alert('Пароли не совпадают');
                confirmInput.focus();
                return false;
            }
        });
    });
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    initPasswordToggles();
    initFormValidation();
});
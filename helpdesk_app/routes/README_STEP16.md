# STEP 16

## Что вынесено

- auth/register flow
- confirm_email
- api_system_time

## Что это даёт

- регистрация и email-confirmation больше не завязаны на прямой вызов legacy route handlers;
- системное время для UI теперь отдается через отдельный сервисный слой;
- auth-контур стал ближе к завершенному bridge-варианту перед полной заменой legacy auth helpers.

# Инструкция по push на GitHub с Personal Access Token

## Шаг 1: Создание Personal Access Token на GitHub

1. Перейдите на GitHub: https://github.com/settings/tokens
2. Нажмите "Generate new token" → "Generate new token (classic)"
3. Задайте название токена (например, "bregus-bot-push")
4. Выберите срок действия (рекомендуется 90 дней или custom)
5. Отметьте права доступа:
   - ✅ `repo` (полный доступ к репозиториям)
6. Нажмите "Generate token"
7. **ВАЖНО:** Скопируйте токен сразу (он показывается только один раз!)

## Шаг 2: Push изменений

Выполните команду:
```bash
cd /root/bregus
git push origin main
```

При запросе:
- **Username:** ваш_github_username (например, bregusone)
- **Password:** вставьте ваш Personal Access Token (НЕ ваш пароль GitHub!)

## Альтернатива: Использование токена напрямую в URL

Если хотите избежать ввода каждый раз, можно использовать токен в URL:

```bash
git remote set-url origin https://YOUR_TOKEN@github.com/bregusone/bregus.git
git push origin main
```

⚠️ **Внимание:** Токен будет виден в истории команд. Используйте этот метод только если уверены в безопасности.

## Проверка статуса

После успешного push проверьте:
```bash
git status
```

Должно быть: "Your branch is up to date with 'origin/main'"


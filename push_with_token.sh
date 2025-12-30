#!/bin/bash
# Скрипт для push с использованием Personal Access Token
# Использование: ./push_with_token.sh YOUR_GITHUB_TOKEN

if [ -z "$1" ]; then
    echo "Использование: $0 YOUR_GITHUB_TOKEN"
    echo ""
    echo "Или установите переменную окружения:"
    echo "export GITHUB_TOKEN=your_token"
    echo "$0"
    exit 1
fi

TOKEN=${GITHUB_TOKEN:-$1}
USERNAME="bregusone"  # Замените на ваш GitHub username если нужно

cd /root/bregus

# Используем токен в URL для push
git push https://${TOKEN}@github.com/bregusone/bregus.git main

echo ""
echo "✅ Push выполнен!"


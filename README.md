# Portfolio Telegram Bot

Мой первый Telegram-бот для портфолио, написанный на Python.

Бот показывает информацию обо мне, мои навыки, проекты и контакты через удобные кнопки Telegram.

## Что умеет бот

- Поддерживает команду /myid
- Поддерживает админ-команду /stats
- Сохраняет статистику пользователей в SQLite
- Использует Railway Volume для хранения базы данных
- Показывает информацию обо мне
- Показывает список навыков
- Показывает проекты
- Показывает контакты
- Поддерживает команду /start
- Поддерживает команду /help
- Работает через кнопки Telegram
- Имеет inline-кнопки со ссылками на GitHub, Telegram и репозиторий проекта
- Развёрнут на Railway и работает 24/7

## Технологии

- SQLite
- Railway Volume
- Python
- Pyrogram
- python-dotenv
- Telegram API
- Git / GitHub
- Railway

## Структура проекта

```text
portfolio_bot/
├─ main.py
├─ .env.example
├─ .gitignore
├─ requirements.txt
└─ README.md
```

## Как запустить проект

1. Скачать проект или склонировать репозиторий:

```bash
git clone https://github.com/Freedomfall/portfolio_bot.git
```

2. Перейти в папку проекта:

```bash
cd portfolio_bot
```

3. Создать виртуальное окружение:

```bash
python -m venv venv
```

4. Активировать виртуальное окружение на Windows:

```bash
venv\Scripts\activate
```

5. Установить зависимости:

```bash
pip install -r requirements.txt
```

6. Создать файл `.env` по примеру `.env.example`:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
DB_PATH=/data/bot_stats.db
```

7. Запустить бота:

```bash
python main.py
```

## Важно

Файл `.env` содержит секретные данные и не должен загружаться на GitHub.

## Автор

Telegram: @freedomfall  
GitHub: https://github.com/Freedomfall  
Email: upvake@gmail.com
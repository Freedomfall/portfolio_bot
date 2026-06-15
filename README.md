# Portfolio Telegram Bot

Мой первый Telegram-бот для портфолио, написанный на Python.

Бот показывает информацию обо мне, мои навыки, проекты и контакты через удобные кнопки Telegram.

## Что умеет бот

- Имеет настроенное меню команд через BotFather
- Имеет описание и About-текст в профиле Telegram-бота
- Принимает обратную связь от пользователей через /feedback
- Позволяет админу отвечать пользователям через /reply
- Имеет админ-панель через /admin
- Показывает техническое описание проекта через /about_project
- Показывает проекты с inline-кнопками
- Отправляет админу уведомления об ошибках
- Показывает информацию обо мне
- Показывает список навыков
- Показывает проекты
- Показывает контакты
- Отправляет админу уведомление о новом пользователе
- Поддерживает админ-команду /test_notify для проверки уведомлений
- Поддерживает админ-рассылку через /broadcast

## Команды

- /start — открыть главное меню
- /help — показать помощь
- /about_project — техническое описание проекта
- /feedback текст — отправить сообщение автору бота
- /myid — узнать свой Telegram ID
- /stats — показать статистику бота, только для владельца
- /test_notify — отправить тестовое уведомление админу
- /broadcast текст — отправить сообщение всем пользователям, только для владельца
- /reply user_id текст — ответить пользователю, только для владельца
- /admin — открыть админ-панель, только для владельца

## Настройки Telegram-бота

Через BotFather настроены:

- список публичных команд
- описание бота
- About-текст бота

## Технологии

- Pyrogram callbacks
- Admin tools
- Error handling
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
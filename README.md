# Portfolio Telegram Bot

Мой Telegram-бот для портфолио, написанный на Python.

Бот показывает информацию обо мне, мои навыки, проекты и контакты через удобные кнопки Telegram.  
Также бот имеет админ-панель, SQLite-базу, обратную связь, мини-игры, защиту от спама и Live Analytics Dashboard.

## Версия

Текущая версия: **1.3.0**

## Что умеет бот

- Показывает главное меню через `/start` и `/menu`
- Показывает информацию обо мне
- Показывает список навыков
- Показывает проекты с inline-кнопками
- Показывает контакты
- Показывает техническое описание проекта через `/about_project`
- Показывает версию и историю обновлений через `/version`
- Показывает roadmap проекта через `/roadmap`
- Показывает privacy-информацию через `/privacy`
- Показывает профиль пользователя через `/profile`
- Показывает Telegram ID через `/myid`
- Поддерживает команду `/ping`
- Поддерживает команды `/status` и `/health`
- Показывает uptime — время работы после последнего запуска
- Принимает обратную связь через `/feedback`
- Имеет антиспам-защиту для `/feedback`
- Имеет общую антиспам-защиту для команд, кнопок и сообщений
- Ограничивает слишком длинные сообщения feedback, reply и broadcast
- Отправляет админу уведомление о новом пользователе
- Отправляет админу уведомления об ошибках
- Позволяет админу отвечать пользователям через `/reply`
- Поддерживает админ-рассылку через `/broadcast`
- Имеет админ-панель через `/admin`
- Имеет кнопку статистики в главном меню
- Показывает статистику бота через `/stats`
- Создаёт резервную копию базы данных через `/backup_db`
- Имеет кнопку backup базы в админ-панели
- Показывает последние сообщения обратной связи через `/last_feedback`
- Имеет кнопку просмотра последних feedback в админ-панели
- Экспортирует пользователей в CSV через `/export_users`
- Экспортирует сообщения обратной связи в CSV через `/export_feedback`
- Экспортирует события аналитики в CSV через `/export_events`
- Ведёт admin logs через таблицу `admin_logs`
- Показывает последние действия админа через `/admin_logs`
- Имеет мини-игру “Орёл или Решка” через `/coin`
- Имеет GIF-анимацию монетки
- Удаляет GIF монетки после ожидания и показывает результат
- Имеет мини-игру “Кубик” через `/dice`
- Имеет GIF-анимацию кубика
- Удаляет GIF кубика после ожидания и показывает результат
- Ведёт игровую статистику в таблице `game_results`
- Показывает статистику игр через `/game_stats`
- Собирает действия пользователей в таблицу `events`
- Имеет Live Analytics Dashboard через `/dashboard`
- Показывает активность за последние дни через `/activity`
- Показывает топ активных пользователей через `/top_users`
- Имеет расширенную админ-панель с callback-кнопками
- Работает 24/7 на Railway
- Использует Railway Volume для сохранения SQLite-базы

## Live Analytics Dashboard

В версии **1.3.0** добавлена аналитическая система.

Бот записывает события пользователей в таблицу `events`:

- команды
- нажатия кнопок меню
- действия в мини-играх
- feedback
- неизвестные сообщения
- действия администратора

Админ может смотреть аналитику прямо в Telegram:

- `/dashboard` — главная аналитическая панель
- `/activity` — активность за последние дни
- `/top_users` — топ пользователей по активности
- `/export_events` — экспорт событий в CSV

## Мини-игры

### Монетка

Команда:

```text
/coin
```

Бот отправляет GIF-анимацию монетки, ждёт несколько секунд, удаляет GIF и показывает результат:

```text
Орёл
```

или

```text
Решка
```

### Кубик

Команда:

```text
/dice
```

Бот отправляет GIF-анимацию кубика, ждёт несколько секунд, удаляет GIF и показывает результат от 1 до 6.

### Статистика игр

Команда:

```text
/game_stats
```

Показывает личную игровую статистику пользователя.

## Команды

### Публичные команды

- `/start` — открыть главное меню
- `/menu` — показать главное меню
- `/help` — показать помощь
- `/about_project` — техническое описание проекта
- `/privacy` — какие данные хранит бот
- `/version` — версия бота и последнее обновление
- `/roadmap` — планы развития проекта
- `/ping` — проверить работу бота и uptime
- `/status` — короткий статус бота
- `/health` — технический health-check
- `/coin` — подбросить монетку Орёл или Решка
- `/dice` — бросить кубик от 1 до 6
- `/game_stats` — посмотреть свою игровую статистику
- `/profile` — посмотреть свою статистику в боте
- `/myid` — узнать свой Telegram ID
- `/feedback текст` — отправить сообщение автору бота

### Команды владельца

- `/admin` — открыть админ-панель
- `/stats` — показать статистику бота
- `/dashboard` — открыть Live Analytics Dashboard
- `/activity` — посмотреть активность за последние дни
- `/top_users` — посмотреть топ пользователей по активности
- `/admin_logs` — посмотреть последние действия админа
- `/test_notify` — отправить тестовое уведомление админу
- `/broadcast текст` — отправить сообщение всем пользователям
- `/reply user_id текст` — ответить пользователю через бота
- `/export_users` — выгрузить пользователей в CSV
- `/export_feedback` — выгрузить обратную связь в CSV
- `/export_events` — выгрузить события аналитики в CSV
- `/last_feedback` — показать последние сообщения обратной связи
- `/backup_db` — скачать резервную копию базы данных

## Админ-панель

Админ-панель открывается командой:

```text
/admin
```

В ней есть быстрые кнопки для:

- статистики
- Live Dashboard
- активности
- топа пользователей
- health-check
- admin logs
- backup базы
- экспорта пользователей
- экспорта feedback
- экспорта events
- последних feedback
- тестового уведомления
- подсказок по рассылке
- подсказок по ответу пользователю

## База данных

Бот использует SQLite.

Основные таблицы:

- `users` — пользователи и статистика запусков
- `feedback` — сообщения обратной связи
- `admin_logs` — действия администратора
- `events` — события аналитики
- `game_results` — результаты мини-игр

На Railway база сохраняется через Railway Volume.

## Настройки Telegram-бота

Через BotFather настроены:

- список публичных команд
- описание бота
- About-текст бота

## Технологии

- Python
- Pyrogram
- python-dotenv
- Telegram API
- SQLite
- CSV export
- tempfile
- Railway
- Railway Volume
- Git / GitHub
- Async handlers
- Callback buttons
- Admin tools
- Error handling
- Global rate limiting
- Event tracking
- Analytics dashboard
- Game statistics
- Environment variables

## Структура проекта

```text
portfolio_bot/
├─ main.py
├─ .env.example
├─ .gitignore
├─ requirements.txt
└─ README.md
```

## Как запустить проект локально

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
DB_PATH=bot_stats.db
COIN_GIF_URL=https://example.com/coin.gif
DICE_GIF_URL=https://example.com/dice.gif
```

7. Запустить бота:

```bash
python main.py
```

## Переменные окружения для Railway

На Railway нужно добавить переменные:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
DB_PATH=/data/bot_stats.db
COIN_GIF_URL=https://example.com/coin.gif
DICE_GIF_URL=https://example.com/dice.gif
```

`COIN_GIF_URL` и `DICE_GIF_URL` должны быть прямыми ссылками на GIF.  
Если GIF-ссылка не задана или не работает, бот использует текстовую fallback-анимацию.

## Проверка перед деплоем

Перед отправкой на GitHub рекомендуется проверить код:

```bash
python -m py_compile main.py
```

Если ошибок нет:

```bash
git add main.py README.md .env.example
git commit -m "Update bot and README"
git push
```

## Важно

Файл `.env` содержит секретные данные и не должен загружаться на GitHub.

В `.gitignore` должны быть скрыты:

```text
.env
venv/
__pycache__/
*.session
*.session-journal
bot_stats.db
```

## Автор

Telegram: @freedomfall  
GitHub: https://github.com/Freedomfall  
Email: upvake@gmail.com

import asyncio
import os
import sqlite3
import traceback
from datetime import datetime

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DB_PATH = os.getenv("DB_PATH", "bot_stats.db")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError(
        "Не найдены API_ID, API_HASH или BOT_TOKEN. "
        "Проверь файл .env или Variables на Railway."
    )

API_ID = int(API_ID)
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None

app = Client(
    "portfolio_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

START_TIME = datetime.now()

def ensure_db_folder_exists():
    folder = os.path.dirname(DB_PATH)

    if folder:
        os.makedirs(folder, exist_ok=True)


def init_db():
    ensure_db_folder_exists()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                launches INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                message TEXT,
                created_at TEXT
            )
            """
        )

        conn.commit()


def save_user(user):
    if user is None:
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT launches FROM users WHERE user_id = ?",
            (user_id,)
        )
        existing_user = cursor.fetchone()

        is_new_user = existing_user is None

        if existing_user:
            cursor.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?, launches = launches + 1, last_seen = ?
                WHERE user_id = ?
                """,
                (username, first_name, now, user_id)
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (user_id, username, first_name, launches, first_seen, last_seen)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (user_id, username, first_name, now, now)
            )

        conn.commit()

    return is_new_user


def save_feedback(user, message_text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO feedback (user_id, username, first_name, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.username or "",
                user.first_name or "",
                message_text,
                now
            )
        )
        conn.commit()


def get_stats_text():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(launches) FROM users")
        total_launches = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_feedback = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT user_id, username, first_name, launches, last_seen
            FROM users
            ORDER BY last_seen DESC
            LIMIT 5
            """
        )
        last_users = cursor.fetchall()

    text = (
        "📊 Статистика бота\n\n"
        f"👥 Уникальных пользователей: {total_users}\n"
        f"🚀 Всего запусков /start: {total_launches}\n"
        f"💬 Сообщений обратной связи: {total_feedback}\n\n"
        "Последние пользователи:\n"
    )

    if not last_users:
        text += "Пока нет данных."
        return text

    for user_id, username, first_name, launches, last_seen in last_users:
        if username:
            user_label = f"@{username}"
        elif first_name:
            user_label = first_name
        else:
            user_label = str(user_id)

        text += f"• {user_label} — запусков: {launches}, последний раз: {last_seen}\n"

    return text

def get_uptime_text():
    now = datetime.now()
    uptime = now - START_TIME

    total_seconds = int(uptime.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return (
        "🏓 Pong!\n\n"
        f"⏱ Uptime: {days}д {hours}ч {minutes}м {seconds}с\n"
        f"🕒 Запущен: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}"
    )

def get_all_user_ids():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

    return [user[0] for user in users]


async def notify_admin_about_new_user(client, user, is_test=False):
    if ADMIN_ID is None or user is None:
        return

    if user.id == ADMIN_ID and not is_test:
        return

    username = f"@{user.username}" if user.username else "не указан"
    first_name = user.first_name or "не указано"
    user_id = user.id
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    title = "🧪 Тестовое уведомление" if is_test else "👤 Новый пользователь"

    text = (
        f"{title}\n\n"
        f"Имя: {first_name}\n"
        f"Username: {username}\n"
        f"ID: {user_id}\n"
        f"Дата: {now}"
    )

    try:
        await client.send_message(ADMIN_ID, text)
    except Exception as error:
        print(f"Не удалось отправить уведомление админу: {error}")


async def notify_admin_about_feedback(client, user, feedback_text):
    if ADMIN_ID is None:
        return

    username = f"@{user.username}" if user.username else "не указан"
    first_name = user.first_name or "не указано"

    text = (
        "💬 Новое сообщение через бота\n\n"
        f"Имя: {first_name}\n"
        f"Username: {username}\n"
        f"ID: `{user.id}`\n\n"
        f"Сообщение:\n{feedback_text}\n\n"
        "Ответить пользователю:\n"
        f"`/reply {user.id} текст ответа`"
    )

    try:
        await client.send_message(ADMIN_ID, text)
    except Exception as error:
        print(f"Не удалось отправить feedback админу: {error}")


async def notify_admin_about_error(client, error, place="unknown"):
    if ADMIN_ID is None:
        return

    error_text = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    if len(error_text) > 3000:
        error_text = error_text[:3000] + "\n\n...обрезано"

    text = (
        "⚠️ Ошибка в боте\n\n"
        f"Место: `{place}`\n\n"
        f"```text\n{error_text}\n```"
    )

    try:
        await client.send_message(ADMIN_ID, text)
    except Exception as send_error:
        print(f"Не удалось отправить ошибку админу: {send_error}")


def handle_errors(handler):
    async def wrapper(client, update):
        try:
            return await handler(client, update)
        except Exception as error:
            await notify_admin_about_error(client, error, handler.__name__)

            try:
                if hasattr(update, "reply_text"):
                    await update.reply_text(
                        "⚠️ Произошла ошибка. Автор бота уже получил уведомление."
                    )
                elif hasattr(update, "message") and update.message:
                    await update.message.reply_text(
                        "⚠️ Произошла ошибка. Автор бота уже получил уведомление."
                    )
            except Exception:
                pass

            print(f"Ошибка в {handler.__name__}: {error}")

    return wrapper


keyboard = ReplyKeyboardMarkup(
    [
        ["👨‍💻 Обо мне", "🛠 Навыки"],
        ["📂 Проекты", "📬 Контакты"],
        ["ℹ️ О проекте", "💬 Связаться"],
        ["❓ Помощь"]
    ],
    resize_keyboard=True
)

start_links = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "🌐 GitHub",
                url="https://github.com/Freedomfall"
            )
        ],
        [
            InlineKeyboardButton(
                "📂 Код проекта",
                url="https://github.com/Freedomfall/portfolio_bot"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Написать мне",
                url="https://t.me/freedomfall"
            )
        ]
    ]
)

contacts_links = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "🌐 Мой GitHub",
                url="https://github.com/Freedomfall"
            )
        ],
        [
            InlineKeyboardButton(
                "📂 Репозиторий проекта",
                url="https://github.com/Freedomfall/portfolio_bot"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Telegram",
                url="https://t.me/freedomfall"
            )
        ]
    ]
)

projects_links = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "🤖 Portfolio Bot",
                url="https://github.com/Freedomfall/portfolio_bot"
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 GitHub профиль",
                url="https://github.com/Freedomfall"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Связаться",
                url="https://t.me/freedomfall"
            )
        ]
    ]
)

admin_panel = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("🏓 Ping / Uptime", callback_data="admin_ping")
        ],
        [
            InlineKeyboardButton("🧪 Тест уведомления", callback_data="admin_test_notify")
        ],
        [
            InlineKeyboardButton("📢 Как сделать рассылку", callback_data="admin_broadcast_help")
        ],
        [
            InlineKeyboardButton("💬 Как ответить пользователю", callback_data="admin_reply_help")
        ]
    ]
)


@app.on_message(filters.command("start"))
@handle_errors
async def start(client, message):
    is_new_user = save_user(message.from_user)

    if is_new_user:
        await notify_admin_about_new_user(client, message.from_user)

    await message.reply_text(
        "Привет! 👋\n\n"
        "Я портфолио-бот Python-разработчика.\n"
        "Я умею показывать проекты, принимать сообщения, собирать статистику "
        "и работать с админ-панелью.\n\n"
        "Выбери раздел ниже:",
        reply_markup=keyboard
    )

    await message.reply_text(
        "🔗 Быстрые ссылки:",
        reply_markup=start_links
    )


@app.on_message(filters.command("help"))
@handle_errors
async def help_command(client, message):
    await message.reply_text(
        "❓ Помощь\n\n"
        "Доступные команды:\n\n"
        "/start — открыть главное меню\n"
        "/help — показать помощь\n"
        "/about_project — техническое описание проекта\n"
	"/ping — проверить работу бота и uptime\n"
        "/feedback текст — написать автору бота\n"
        "/myid — узнать свой Telegram ID\n"
        "/stats — статистика бота, только для владельца\n"
        "/test_notify — проверить уведомление админу\n"
        "/broadcast текст — рассылка всем пользователям, только для владельца\n"
        "/reply user_id текст — ответить пользователю, только для владельца\n"
        "/admin — админ-панель, только для владельца\n\n"
        "Также можно пользоваться кнопками меню.",
        reply_markup=keyboard
    )


@app.on_message(filters.command("about_project"))
@handle_errors
async def about_project_command(client, message):
    await message.reply_text(
        "ℹ️ О проекте\n\n"
        "Этот бот — портфолио-проект на Python.\n\n"
        "Техническая часть:\n"
        "• Python\n"
        "• Pyrogram\n"
        "• SQLite\n"
        "• Railway Deploy\n"
        "• Railway Volume для базы данных\n"
        "• Git и GitHub\n"
        "• .env переменные для секретов\n"
        "• Админ-команды\n"
        "• Обратная связь от пользователей\n"
        "• Рассылка всем пользователям\n"
        "• Уведомления админу\n"
        "• Обработка ошибок\n\n"
        "Код проекта:\n"
        "https://github.com/Freedomfall/portfolio_bot"
    )

@app.on_message(filters.command("ping"))
@handle_errors
async def ping_command(client, message):
    await message.reply_text(get_uptime_text())

@app.on_message(filters.command("myid"))
@handle_errors
async def myid_command(client, message):
    await message.reply_text(
        f"🆔 Твой Telegram ID:\n\n`{message.from_user.id}`"
    )


@app.on_message(filters.command("stats"))
@handle_errors
async def stats_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text(
            "⚠️ ADMIN_ID пока не задан.\n\n"
            "Напиши команду /myid, скопируй свой Telegram ID "
            "и добавь его в Railway Variables как ADMIN_ID."
        )
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к статистике.")
        return

    await message.reply_text(get_stats_text())


@app.on_message(filters.command("admin"))
@handle_errors
async def admin_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text("⚠️ ADMIN_ID пока не задан.")
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к админ-панели.")
        return

    await message.reply_text(
        "🛠 Админ-панель\n\n"
        "Выбери действие:",
        reply_markup=admin_panel
    )


@app.on_callback_query()
@handle_errors
async def callback_handler(client, callback_query):
    if ADMIN_ID is None or callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ Нет доступа", show_alert=True)
        return

    data = callback_query.data

    if data == "admin_stats":
        await callback_query.answer("Готово")
        await callback_query.message.reply_text(get_stats_text())

    elif data == "admin_ping":
        await callback_query.answer("Pong")
        await callback_query.message.reply_text(get_uptime_text())

    elif data == "admin_test_notify":
        await callback_query.answer("Отправляю тест")
        await notify_admin_about_new_user(
            client,
            callback_query.from_user,
            is_test=True
        )
        await callback_query.message.reply_text("✅ Тестовое уведомление отправлено.")

    elif data == "admin_broadcast_help":
        await callback_query.answer("Инструкция")
        await callback_query.message.reply_text(
            "📢 Рассылка\n\n"
            "Используй команду:\n"
            "`/broadcast текст сообщения`\n\n"
            "Пример:\n"
            "`/broadcast Привет! Я обновил бота 🚀`"
        )

    elif data == "admin_reply_help":
        await callback_query.answer("Инструкция")
        await callback_query.message.reply_text(
            "💬 Ответ пользователю\n\n"
            "Используй команду:\n"
            "`/reply user_id текст ответа`\n\n"
            "Пример:\n"
            "`/reply 123456789 Привет! Спасибо за сообщение.`"
        )


@app.on_message(filters.command("test_notify"))
@handle_errors
async def test_notify_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text("⚠️ ADMIN_ID пока не задан.")
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    await notify_admin_about_new_user(client, message.from_user, is_test=True)
    await message.reply_text("✅ Тестовое уведомление отправлено админу.")


@app.on_message(filters.command("feedback"))
@handle_errors
async def feedback_command(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "💬 Обратная связь\n\n"
            "Напиши сообщение после команды.\n\n"
            "Пример:\n"
            "`/feedback Привет! Хочу обсудить проект.`"
        )
        return

    feedback_text = message.text.split(maxsplit=1)[1]

    save_user(message.from_user)
    save_feedback(message.from_user, feedback_text)

    await notify_admin_about_feedback(client, message.from_user, feedback_text)

    await message.reply_text(
        "✅ Сообщение отправлено автору бота.\n"
        "Спасибо за обратную связь!"
    )


@app.on_message(filters.command("reply"))
@handle_errors
async def reply_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text("⚠️ ADMIN_ID пока не задан.")
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    if len(message.command) < 3:
        await message.reply_text(
            "💬 Использование команды:\n\n"
            "`/reply user_id текст ответа`\n\n"
            "Пример:\n"
            "`/reply 123456789 Привет! Спасибо за сообщение.`"
        )
        return

    parts = message.text.split(maxsplit=2)

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.reply_text("⚠️ user_id должен быть числом.")
        return

    reply_text = parts[2]

    try:
        await client.send_message(
            target_user_id,
            "💬 Ответ от автора бота:\n\n"
            f"{reply_text}"
        )
        await message.reply_text("✅ Ответ отправлен пользователю.")
    except Exception as error:
        await message.reply_text(f"⚠️ Не удалось отправить ответ: {error}")


@app.on_message(filters.command("broadcast"))
@handle_errors
async def broadcast_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text("⚠️ ADMIN_ID пока не задан.")
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    if len(message.command) < 2:
        await message.reply_text(
            "📢 Использование команды:\n\n"
            "`/broadcast текст сообщения`\n\n"
            "Пример:\n"
            "`/broadcast Привет! Я обновил бота 🚀`"
        )
        return

    broadcast_text = message.text.split(maxsplit=1)[1]
    user_ids = get_all_user_ids()

    sent_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            await client.send_message(
                user_id,
                "📢 Сообщение от автора бота:\n\n"
                f"{broadcast_text}"
            )
            sent_count += 1

        except FloodWait as error:
            await asyncio.sleep(error.value)

            try:
                await client.send_message(
                    user_id,
                    "📢 Сообщение от автора бота:\n\n"
                    f"{broadcast_text}"
                )
                sent_count += 1
            except Exception as retry_error:
                failed_count += 1
                print(f"Не удалось отправить после ожидания {user_id}: {retry_error}")

        except Exception as error:
            failed_count += 1
            print(f"Не удалось отправить сообщение пользователю {user_id}: {error}")

    await message.reply_text(
        "✅ Рассылка завершена\n\n"
        f"Отправлено: {sent_count}\n"
        f"Ошибок: {failed_count}"
    )


@app.on_message(
    filters.text
    & filters.private
    & ~filters.command(
        [
            "start",
            "help",
            "about_project",
            "ping",
            "myid",
            "stats",
            "admin",
            "test_notify",
            "feedback",
            "reply",
            "broadcast",
        ]
    )
)
@handle_errors
async def menu(client, message):
    text = message.text

    if text == "👨‍💻 Обо мне":
        await message.reply_text(
            "👨‍💻 Обо мне\n\n"
            "Привет! Меня зовут Freedomfall.\n"
            "Я изучаю Python и создаю Telegram-ботов.\n\n"
            "Этот бот — мой первый проект для портфолио, "
            "но он уже умеет работать со статистикой, базой данных, "
            "админ-панелью и обратной связью."
        )

    elif text == "🛠 Навыки":
        await message.reply_text(
            "🛠 Мои навыки\n\n"
            "• Python\n"
            "• Telegram-боты\n"
            "• Pyrogram\n"
            "• SQLite\n"
            "• Git и GitHub\n"
            "• Railway Deploy\n"
            "• Работа с переменными окружения\n"
            "• Основы backend-разработки"
        )

    elif text == "📂 Проекты":
        await message.reply_text(
            "📂 Мои проекты\n\n"
            "1. Portfolio Bot — бот-визитка в Telegram\n"
            "2. Todo Bot — бот для задач, скоро\n"
            "3. Weather Bot — бот погоды, скоро\n\n"
            "Ниже есть кнопки со ссылками:",
            reply_markup=projects_links
        )

    elif text == "📬 Контакты":
        await message.reply_text(
            "📬 Контакты\n\n"
            "Telegram: @freedomfall\n"
            "GitHub: https://github.com/Freedomfall\n"
            "Email: upvake@gmail.com",
            reply_markup=contacts_links
        )

    elif text == "ℹ️ О проекте":
        await about_project_command(client, message)

    elif text == "💬 Связаться":
        await message.reply_text(
            "💬 Связаться со мной\n\n"
            "Напиши сообщение командой:\n\n"
            "`/feedback твой текст`\n\n"
            "Пример:\n"
            "`/feedback Привет! Хочу обсудить Telegram-бота.`"
        )

    elif text == "❓ Помощь":
        await help_command(client, message)

    else:
        await message.reply_text(
            "Я пока не понимаю это сообщение 😅\n"
            "Нажми одну из кнопок ниже или используй команду /help.",
            reply_markup=keyboard
        )


init_db()
app.run()
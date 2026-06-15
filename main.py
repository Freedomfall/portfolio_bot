import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DB_PATH = os.getenv("DB_PATH", "bot_stats.db")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError("Не найдены API_ID, API_HASH или BOT_TOKEN. Проверь файл .env или Variables на Railway.")

API_ID = int(API_ID)
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None

app = Client(
    "portfolio_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


def init_db():
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


def get_stats_text():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(launches) FROM users")
        total_launches = cursor.fetchone()[0] or 0

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
        f"🚀 Всего запусков /start: {total_launches}\n\n"
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


keyboard = ReplyKeyboardMarkup(
    [
        ["👨‍💻 Обо мне", "🛠 Навыки"],
        ["📂 Проекты", "📬 Контакты"],
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


@app.on_message(filters.command("start"))
async def start(client, message):
    is_new_user = save_user(message.from_user)

    if is_new_user:
        await notify_admin_about_new_user(client, message.from_user)

    await message.reply_text(
        "Привет! 👋\n\n"
        "Я портфолио-бот начинающего Python-разработчика.\n"
        "Я умею показывать информацию обо мне, мои навыки, проекты и контакты.\n\n"
        "Выбери раздел ниже:",
        reply_markup=keyboard
    )

    await message.reply_text(
        "🔗 Быстрые ссылки:",
        reply_markup=start_links
    )


@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply_text(
        "❓ Помощь\n\n"
        "Доступные команды:\n\n"
        "/start — открыть главное меню\n"
        "/help — показать помощь\n"
        "/myid — узнать свой Telegram ID\n"
        "/stats — статистика бота, только для владельца\n"
        "/test_notify — проверить уведомление админу\n\n"
        "Также можно пользоваться кнопками:\n"
        "👨‍💻 Обо мне\n"
        "🛠 Навыки\n"
        "📂 Проекты\n"
        "📬 Контакты",
        reply_markup=keyboard
    )


@app.on_message(filters.command("myid"))
async def myid_command(client, message):
    await message.reply_text(
        f"🆔 Твой Telegram ID:\n\n`{message.from_user.id}`"
    )


@app.on_message(filters.command("stats"))
async def stats_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text(
            "⚠️ ADMIN_ID пока не задан.\n\n"
            "Напиши команду /myid, скопируй свой Telegram ID и добавь его в Railway Variables как ADMIN_ID."
        )
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к статистике.")
        return

    await message.reply_text(get_stats_text())


@app.on_message(filters.command("test_notify"))
async def test_notify_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text("⚠️ ADMIN_ID пока не задан.")
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    await notify_admin_about_new_user(client, message.from_user, is_test=True)
    await message.reply_text("✅ Тестовое уведомление отправлено админу.")


@app.on_message(filters.text & filters.private & ~filters.command(["start", "help", "myid", "stats", "test_notify"]))
async def menu(client, message):
    text = message.text

    if text == "👨‍💻 Обо мне":
        await message.reply_text(
            "👨‍💻 Обо мне\n\n"
            "Привет! Меня зовут Freedomfall.\n"
            "Я изучаю Python и создаю Telegram-ботов.\n\n"
            "Этот бот — мой первый проект для портфолио."
        )

    elif text == "🛠 Навыки":
        await message.reply_text(
            "🛠 Мои навыки\n\n"
            "• Python\n"
            "• Telegram-боты\n"
            "• Работа с API\n"
            "• Git и GitHub\n"
            "• Основы баз данных\n"
            "• Деплой проекта на Railway"
        )

    elif text == "📂 Проекты":
        await message.reply_text(
            "📂 Мои проекты\n\n"
            "1. Portfolio Bot — бот-визитка в Telegram\n"
            "2. Todo Bot — бот для задач, скоро\n"
            "3. Weather Bot — бот погоды, скоро\n\n"
            "Код этого проекта:\n"
            "https://github.com/Freedomfall/portfolio_bot"
        )

    elif text == "📬 Контакты":
        await message.reply_text(
            "📬 Контакты\n\n"
            "Telegram: @freedomfall\n"
            "GitHub: https://github.com/Freedomfall\n"
            "Email: upvake@gmail.com",
            reply_markup=contacts_links
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
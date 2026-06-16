import asyncio
import csv
import os
import random
import sqlite3
import tempfile
import time
import traceback
from contextlib import contextmanager
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

# =========================
# CONFIG
# =========================

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DB_PATH = os.getenv("DB_PATH", "bot_stats.db")
COIN_GIF_URL = os.getenv("COIN_GIF_URL", "")
DICE_GIF_URL = os.getenv("DICE_GIF_URL", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError(
        "Не найдены API_ID, API_HASH или BOT_TOKEN. "
        "Проверь файл .env или Variables на Railway."
    )

try:
    API_ID = int(API_ID)
except ValueError as error:
    raise RuntimeError("API_ID должен быть числом.") from error

try:
    ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None
except ValueError as error:
    raise RuntimeError("ADMIN_ID должен быть числом.") from error

app = Client(
    "portfolio_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# =========================
# STANDARDS / LIMITS
# =========================

START_TIME = datetime.now()
BOT_VERSION = "1.2.0"
LAST_UPDATE = "2026-06-16"

FEEDBACK_COOLDOWN_SECONDS = 60
GLOBAL_RATE_LIMIT_SECONDS = 2
MAX_FEEDBACK_LENGTH = 1500
MAX_BROADCAST_LENGTH = 3500
MAX_REPLY_LENGTH = 3500
ADMIN_LOGS_LIMIT = 10

USER_LAST_ACTION = {}


PUBLIC_COMMANDS = {
    "start": "открыть главное меню",
    "menu": "показать главное меню",
    "help": "показать помощь",
    "about_project": "техническое описание проекта",
    "privacy": "какие данные хранит бот",
    "version": "версия бота и последнее обновление",
    "roadmap": "планы развития проекта",
    "ping": "проверить работу бота и uptime",
    "status": "короткий статус бота",
    "health": "технический health-check",
    "coin": "подбросить монетку Орёл или Решка",
    "dice": "бросить кубик от 1 до 6",
    "profile": "посмотреть свою статистику в боте",
    "myid": "узнать свой Telegram ID",
    "feedback": "написать автору бота: /feedback текст",
}

ADMIN_COMMANDS = {
    "admin": "админ-панель, только для владельца",
    "stats": "статистика бота, только для владельца",
    "test_notify": "проверить уведомление админу",
    "broadcast": "рассылка всем пользователям: /broadcast текст",
    "reply": "ответить пользователю: /reply user_id текст",
    "export_users": "выгрузить пользователей в CSV",
    "export_feedback": "выгрузить обратную связь в CSV",
    "last_feedback": "последние сообщения обратной связи",
    "backup_db": "скачать резервную копию базы",
    "admin_logs": "последние действия админа",
}

ALL_COMMANDS = list(PUBLIC_COMMANDS.keys()) + list(ADMIN_COMMANDS.keys())


# =========================
# SMALL HELPERS
# =========================

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text, max_length):
    if text is None:
        return ""

    text = str(text).strip()

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


def is_admin_user_id(user_id):
    return ADMIN_ID is not None and user_id == ADMIN_ID


def get_user_label(user_id=None, username=None, first_name=None):
    if username:
        return f"@{username}"

    if first_name:
        return first_name

    if user_id is not None:
        return str(user_id)

    return "неизвестный пользователь"


def ensure_db_folder_exists():
    folder = os.path.dirname(DB_PATH)

    if folder:
        os.makedirs(folder, exist_ok=True)


@contextmanager
def db_connection():
    ensure_db_folder_exists()

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# =========================
# DATABASE
# =========================

def init_db():
    with db_connection() as conn:
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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TEXT
            )
            """
        )


def save_user(user):
    if user is None:
        return False

    current_time = now_text()

    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""

    with db_connection() as conn:
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
                (username, first_name, current_time, user_id)
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (user_id, username, first_name, launches, first_seen, last_seen)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (user_id, username, first_name, current_time, current_time)
            )

    return is_new_user


def ensure_user_record(user):
    if user is None:
        return False

    current_time = now_text()

    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user.id,)
        )
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?, last_seen = ?
                WHERE user_id = ?
                """,
                (
                    user.username or "",
                    user.first_name or "",
                    current_time,
                    user.id
                )
            )
            return False

        cursor.execute(
            """
            INSERT INTO users (user_id, username, first_name, launches, first_seen, last_seen)
            VALUES (?, ?, ?, 0, ?, ?)
            """,
            (
                user.id,
                user.username or "",
                user.first_name or "",
                current_time,
                current_time
            )
        )
        return True


def touch_user(user):
    if user is None:
        return

    current_time = now_text()

    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET username = ?, first_name = ?, last_seen = ?
            WHERE user_id = ?
            """,
            (
                user.username or "",
                user.first_name or "",
                current_time,
                user.id
            )
        )


def save_feedback(user, message_text):
    with db_connection() as conn:
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
                now_text()
            )
        )


def log_admin_action(admin_id, action, details=""):
    if admin_id is None:
        return

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO admin_logs (admin_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                admin_id,
                truncate_text(action, 100),
                truncate_text(details, 1000),
                now_text()
            )
        )


def get_feedback_wait_seconds(user_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT created_at
            FROM feedback
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()

    if not row:
        return 0

    try:
        last_feedback_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return 0

    passed_seconds = int((datetime.now() - last_feedback_time).total_seconds())

    if passed_seconds >= FEEDBACK_COOLDOWN_SECONDS:
        return 0

    return FEEDBACK_COOLDOWN_SECONDS - passed_seconds


def get_all_user_ids():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

    return [user[0] for user in users]


# =========================
# TEXT BUILDERS
# =========================

def get_stats_text():
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(launches) FROM users")
        total_launches = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_feedback = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM admin_logs")
        total_admin_logs = cursor.fetchone()[0]

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
        f"💬 Сообщений обратной связи: {total_feedback}\n"
        f"🧾 Записей в admin logs: {total_admin_logs}\n\n"
        "Последние пользователи:\n"
    )

    if not last_users:
        return text + "Пока нет данных."

    for user_id, username, first_name, launches, last_seen in last_users:
        user_label = get_user_label(user_id, username, first_name)
        text += f"• {user_label} — запусков: {launches}, последний раз: {last_seen}\n"

    return text


def get_last_feedback_text(limit=5):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, username, first_name, message, created_at
            FROM feedback
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()

    if not rows:
        return "💬 Последние сообщения\n\nПока нет сообщений обратной связи."

    text = "💬 Последние сообщения обратной связи\n\n"

    for user_id, username, first_name, message, created_at in rows:
        user_label = get_user_label(user_id, username, first_name)
        short_message = truncate_text(message, 300)

        text += (
            f"👤 {user_label}\n"
            f"ID: `{user_id}`\n"
            f"Дата: {created_at}\n"
            f"Сообщение: {short_message}\n\n"
        )

    return text


def get_admin_logs_text(limit=ADMIN_LOGS_LIMIT):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT admin_id, action, details, created_at
            FROM admin_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()

    if not rows:
        return "🧾 Admin logs\n\nПока нет записей."

    text = "🧾 Последние действия админа\n\n"

    for admin_id, action, details, created_at in rows:
        text += (
            f"• {created_at}\n"
            f"  Admin ID: `{admin_id}`\n"
            f"  Action: `{action}`\n"
        )

        if details:
            text += f"  Details: {truncate_text(details, 250)}\n"

        text += "\n"

    return text


def get_help_text():
    public_lines = "\n".join(
        f"/{command} — {description}"
        for command, description in PUBLIC_COMMANDS.items()
    )

    admin_lines = "\n".join(
        f"/{command} — {description}"
        for command, description in ADMIN_COMMANDS.items()
    )

    return (
        "❓ Помощь\n\n"
        "Публичные команды:\n\n"
        f"{public_lines}\n\n"
        "Команды владельца:\n\n"
        f"{admin_lines}\n\n"
        "Также можно пользоваться кнопками меню."
    )


def get_about_project_text():
    return (
        "ℹ️ О проекте\n\n"
        "Этот бот — портфолио-проект на Python.\n\n"
        "Стандарты и архитектура:\n"
        "• Pyrogram async handlers\n"
        "• SQLite с отдельными таблицами users, feedback и admin_logs\n"
        "• Единая обработка ошибок\n"
        "• Единая антиспам-защита для пользователей\n"
        "• Ограничения длины feedback, reply и broadcast\n"
        "• Централизованные тексты help/about/version\n"
        "• Админ-панель с callback-кнопками\n"
        "• Логирование действий админа\n"
        "• CSV-экспорт пользователей и feedback\n"
        "• Backup базы данных\n"
        "• GIF/text fallback для игры с монеткой\n"
        "• Railway Deploy 24/7 и Railway Volume\n\n"
        "Код проекта:\n"
        "https://github.com/Freedomfall/portfolio_bot"
    )


def get_coin_text():
    result = random.choice(["Орёл", "Решка"])
    emoji = "🦅" if result == "Орёл" else "🪙"

    return (
        "🪙 Монетка упала!\n\n"
        f"{emoji} Результат: {result}"
    )


async def send_coin_animation(message):
    if COIN_GIF_URL:
        try:
            animation_message = await message.reply_animation(
                COIN_GIF_URL,
                caption="🪙 Подбрасываю монетку..."
            )

            await asyncio.sleep(4)

            try:
                await animation_message.delete()
            except Exception as error:
                print(f"Не удалось удалить GIF монетки: {error}")

            await message.reply_text(get_coin_text())
            return

        except Exception as error:
            print(f"Не удалось отправить GIF монетки: {error}")

    coin_message = await message.reply_text("🪙 Подбрасываю монетку.")

    await asyncio.sleep(0.5)
    await coin_message.edit_text("🪙 Подбрасываю монетку..")

    await asyncio.sleep(0.5)
    await coin_message.edit_text("🪙 Подбрасываю монетку...")

    await asyncio.sleep(0.5)
    await coin_message.edit_text(get_coin_text())


def get_dice_text(number=None):
    if number is None:
        number = random.randint(1, 6)

    return (
        "🎲 Кубик брошен!\n\n"
        f"Выпало число: {number}"
    )


async def send_dice_animation(message):
    number = random.randint(1, 6)

    if DICE_GIF_URL:
        try:
            dice_gif_message = await message.reply_animation(
                DICE_GIF_URL,
                caption="🎲 Бросаю кубик..."
            )

            await asyncio.sleep(4)

            try:
                await dice_gif_message.delete()
            except Exception as error:
                print(f"Не удалось удалить GIF кубика: {error}")

            await message.reply_text(get_dice_text(number))
            return

        except Exception as error:
            print(f"Не удалось отправить GIF кубика: {error}")

    dice_message = await message.reply_text("🎲 Бросаю кубик.")

    await asyncio.sleep(0.5)
    await dice_message.edit_text("🎲 Бросаю кубик..")

    await asyncio.sleep(0.5)
    await dice_message.edit_text("🎲 Бросаю кубик...")

    await asyncio.sleep(0.5)
    await dice_message.edit_text(get_dice_text(number))


def get_version_text():
    return (
        "🚀 Версия бота\n\n"
        f"Версия: {BOT_VERSION}\n"
        f"Последнее обновление: {LAST_UPDATE}\n\n"
        "Что нового в версии 1.2.0:\n"
        "• Добавлены стандарты структуры кода\n"
        "• Добавлена таблица admin_logs\n"
        "• Добавлена команда /admin_logs\n"
        "• Добавлены /menu, /profile, /status и /health\n"
        "• Улучшена антиспам-защита\n"
        "• Добавлены лимиты длины сообщений\n"
        "• Улучшена анимация монетки с GIF fallback"
    )


def get_roadmap_text():
    return (
        "🧭 Roadmap проекта\n\n"
        "Реализовано сейчас:\n"
        "• Портфолио-меню\n"
        "• Статистика SQLite\n"
        "• Админ-панель\n"
        "• Feedback и reply\n"
        "• Broadcast\n"
        "• CSV export\n"
        "• Backup базы\n"
        "• Admin logs\n"
        "• Общий антиспам\n"
        "• Мини-игры\n\n"
        "Следующие идеи:\n"
        "• Карточки проектов с изображениями\n"
        "• Поддержка нескольких языков\n"
        "• Webhook-режим\n"
        "• Отдельная таблица проектов\n"
        "• Todo Bot как второй проект\n"
        "• Weather Bot как третий проект"
    )


def get_privacy_text():
    return (
        "🔐 Privacy / Данные пользователя\n\n"
        "Этот бот хранит минимальные данные, необходимые для работы функций:\n\n"
        "• Telegram ID — для статистики и ответа через бота\n"
        "• Username — чтобы автор мог понять, кто написал\n"
        "• Имя Telegram — для удобного отображения в админ-панели\n"
        "• Время первого и последнего запуска — для статистики\n"
        "• Сообщения /feedback — чтобы автор мог прочитать обратную связь\n\n"
        "Данные используются только внутри этого портфолио-бота.\n"
        "Они не продаются, не передаются третьим лицам и не используются для рекламы.\n\n"
        "Если хочешь связаться с автором напрямую:\n"
        "@freedomfall"
    )


def get_uptime_text():
    uptime = datetime.now() - START_TIME
    total_seconds = int(uptime.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return (
        "🏓 Pong!\n\n"
        f"⏱ Uptime: {days}д {hours}ч {minutes}м {seconds}с\n"
        f"🕒 Запущен: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🤖 Версия: {BOT_VERSION}"
    )


def get_health_text():
    db_status = "ok"

    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as error:
        db_status = f"error: {error}"

    return (
        "🟢 Health-check\n\n"
        f"Bot: ok\n"
        f"DB: {db_status}\n"
        f"Version: {BOT_VERSION}\n"
        f"Time: {now_text()}"
    )


def get_profile_text(user):
    if user is None:
        return "👤 Профиль\n\nНе удалось определить пользователя."

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT username, first_name, launches, first_seen, last_seen
            FROM users
            WHERE user_id = ?
            """,
            (user.id,)
        )
        row = cursor.fetchone()

    if not row:
        return (
            "👤 Твой профиль\n\n"
            f"ID: `{user.id}`\n"
            "Ты ещё не запускал /start, поэтому статистики пока нет."
        )

    username, first_name, launches, first_seen, last_seen = row
    user_label = get_user_label(user.id, username, first_name)

    return (
        "👤 Твой профиль в боте\n\n"
        f"Пользователь: {user_label}\n"
        f"ID: `{user.id}`\n"
        f"Запусков /start: {launches}\n"
        f"Первый запуск: {first_seen}\n"
        f"Последняя активность: {last_seen}"
    )


# =========================
# EXPORTS
# =========================

def create_users_export():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, username, first_name, launches, first_seen, last_seen
            FROM users
            ORDER BY last_seen DESC
            """
        )
        rows = cursor.fetchall()

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        newline="",
        encoding="utf-8-sig",
        suffix=".csv"
    )

    with temp_file:
        writer = csv.writer(temp_file)
        writer.writerow(
            [
                "user_id",
                "username",
                "first_name",
                "launches",
                "first_seen",
                "last_seen"
            ]
        )
        writer.writerows(rows)

    return temp_file.name, len(rows)


def create_feedback_export():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, username, first_name, message, created_at
            FROM feedback
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        newline="",
        encoding="utf-8-sig",
        suffix=".csv"
    )

    with temp_file:
        writer = csv.writer(temp_file)
        writer.writerow(
            [
                "id",
                "user_id",
                "username",
                "first_name",
                "message",
                "created_at"
            ]
        )
        writer.writerows(rows)

    return temp_file.name, len(rows)


async def send_csv_file(client, chat_id, file_path, caption):
    try:
        await client.send_document(
            chat_id,
            file_path,
            caption=caption
        )
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


# =========================
# NOTIFICATIONS
# =========================

async def notify_admin_about_new_user(client, user, is_test=False):
    if ADMIN_ID is None or user is None:
        return

    if user.id == ADMIN_ID and not is_test:
        return

    username = f"@{user.username}" if user.username else "не указан"
    first_name = user.first_name or "не указано"
    title = "🧪 Тестовое уведомление" if is_test else "👤 Новый пользователь"

    text = (
        f"{title}\n\n"
        f"Имя: {first_name}\n"
        f"Username: {username}\n"
        f"ID: `{user.id}`\n"
        f"Дата: {now_text()}"
    )

    try:
        await client.send_message(ADMIN_ID, text)
    except Exception as error:
        print(f"Не удалось отправить уведомление админу: {error}")


async def notify_admin_about_feedback(client, user, feedback_text):
    if ADMIN_ID is None or user is None:
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


# =========================
# RATE LIMIT / ERRORS
# =========================

def get_user_id_from_update(update):
    if hasattr(update, "from_user") and update.from_user:
        return update.from_user.id

    if hasattr(update, "message") and update.message and update.message.from_user:
        return update.message.from_user.id

    return None


def get_user_from_update(update):
    if hasattr(update, "from_user") and update.from_user:
        return update.from_user

    if hasattr(update, "message") and update.message and update.message.from_user:
        return update.message.from_user

    return None


def get_global_rate_limit_wait_seconds(user_id):
    now = time.monotonic()
    last_action_time = USER_LAST_ACTION.get(user_id)

    if last_action_time is None:
        USER_LAST_ACTION[user_id] = now
        return 0

    passed_seconds = now - last_action_time

    if passed_seconds < GLOBAL_RATE_LIMIT_SECONDS:
        return max(1, int(GLOBAL_RATE_LIMIT_SECONDS - passed_seconds) + 1)

    USER_LAST_ACTION[user_id] = now
    return 0


async def send_rate_limit_warning(update, wait_seconds):
    text = (
        "⏳ Не так быстро.\n\n"
        f"Попробуй ещё раз через {wait_seconds} сек."
    )

    if hasattr(update, "answer"):
        await update.answer(
            f"⏳ Не так быстро. Подожди {wait_seconds} сек.",
            show_alert=False
        )
        return

    if hasattr(update, "reply_text"):
        await update.reply_text(text)


def handle_errors(handler):
    async def wrapper(client, update):
        try:
            user_id = get_user_id_from_update(update)

            if user_id is not None and not is_admin_user_id(user_id):
                wait_seconds = get_global_rate_limit_wait_seconds(user_id)

                if wait_seconds > 0:
                    await send_rate_limit_warning(update, wait_seconds)
                    return

            user = get_user_from_update(update)
            touch_user(user)

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


# =========================
# KEYBOARDS
# =========================

keyboard = ReplyKeyboardMarkup(
    [
        ["👨‍💻 Обо мне", "🛠 Навыки"],
        ["📂 Проекты", "📬 Контакты"],
        ["ℹ️ О проекте", "💬 Связаться"],
        ["🚀 Версия", "🧭 Roadmap"],
        ["🪙 Монетка", "🎲 Кубик"],
        ["📊 Статистика", "🔐 Privacy"],
        ["👤 Профиль", "❓ Помощь"],
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
            InlineKeyboardButton("🟢 Health-check", callback_data="admin_health")
        ],
        [
            InlineKeyboardButton("🧾 Admin logs", callback_data="admin_logs")
        ],
        [
            InlineKeyboardButton("🗄 Backup базы", callback_data="admin_backup_db")
        ],
        [
            InlineKeyboardButton("📥 Экспорт пользователей", callback_data="admin_export_users")
        ],
        [
            InlineKeyboardButton("💬 Экспорт feedback", callback_data="admin_export_feedback")
        ],
        [
            InlineKeyboardButton("💬 Последние feedback", callback_data="admin_last_feedback")
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


# =========================
# HANDLERS
# =========================

@app.on_message(filters.command("start"))
@handle_errors
async def start(client, message):
    is_new_user = save_user(message.from_user)

    if is_new_user:
        await notify_admin_about_new_user(client, message.from_user)

    await message.reply_text(
        "Привет! 👋\n\n"
        "Я портфолио-бот Python-разработчика.\n"
        "Я умею показывать проекты, принимать сообщения, собирать статистику, "
        "работать с админ-панелью и вести admin logs.\n\n"
        "Выбери раздел ниже:",
        reply_markup=keyboard
    )

    await message.reply_text(
        "🔗 Быстрые ссылки:",
        reply_markup=start_links
    )


@app.on_message(filters.command("menu"))
@handle_errors
async def menu_command(client, message):
    await message.reply_text(
        "📋 Главное меню открыто.",
        reply_markup=keyboard
    )


@app.on_message(filters.command("help"))
@handle_errors
async def help_command(client, message):
    await message.reply_text(
        get_help_text(),
        reply_markup=keyboard
    )


@app.on_message(filters.command("about_project"))
@handle_errors
async def about_project_command(client, message):
    await message.reply_text(get_about_project_text())


@app.on_message(filters.command("coin"))
@handle_errors
async def coin_command(client, message):
    await send_coin_animation(message)


@app.on_message(filters.command("dice"))
@handle_errors
async def dice_command(client, message):
    await send_dice_animation(message)


@app.on_message(filters.command("privacy"))
@handle_errors
async def privacy_command(client, message):
    await message.reply_text(get_privacy_text())


@app.on_message(filters.command("version"))
@handle_errors
async def version_command(client, message):
    await message.reply_text(get_version_text())


@app.on_message(filters.command("roadmap"))
@handle_errors
async def roadmap_command(client, message):
    await message.reply_text(get_roadmap_text())


@app.on_message(filters.command(["ping", "status", "health"]))
@handle_errors
async def ping_command(client, message):
    command = message.command[0].lower()

    if command == "health":
        await message.reply_text(get_health_text())
        return

    await message.reply_text(get_uptime_text())


@app.on_message(filters.command(["profile", "me"]))
@handle_errors
async def profile_command(client, message):
    await message.reply_text(get_profile_text(message.from_user))


@app.on_message(filters.command("myid"))
@handle_errors
async def myid_command(client, message):
    await message.reply_text(
        f"🆔 Твой Telegram ID:\n\n`{message.from_user.id}`"
    )


@app.on_message(filters.command("stats"))
@handle_errors
async def stats_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к статистике.")
        return

    log_admin_action(message.from_user.id, "stats", "Открыта статистика через команду /stats")
    await message.reply_text(get_stats_text())


@app.on_message(filters.command("admin"))
@handle_errors
async def admin_command(client, message):
    if ADMIN_ID is None:
        await message.reply_text("⚠️ ADMIN_ID пока не задан.")
        return

    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к админ-панели.")
        return

    log_admin_action(message.from_user.id, "admin_panel", "Открыта админ-панель")

    await message.reply_text(
        "🛠 Админ-панель\n\n"
        "Выбери действие:",
        reply_markup=admin_panel
    )


@app.on_callback_query()
@handle_errors
async def callback_handler(client, callback_query):
    if ADMIN_ID is None or not is_admin_user_id(callback_query.from_user.id):
        await callback_query.answer("⛔ Нет доступа", show_alert=True)
        return

    data = callback_query.data

    if data == "admin_stats":
        await callback_query.answer("Готово")
        log_admin_action(callback_query.from_user.id, "admin_stats", "Статистика из админ-панели")
        await callback_query.message.reply_text(get_stats_text())

    elif data == "admin_ping":
        await callback_query.answer("Pong")
        log_admin_action(callback_query.from_user.id, "admin_ping", "Ping из админ-панели")
        await callback_query.message.reply_text(get_uptime_text())

    elif data == "admin_health":
        await callback_query.answer("Health-check")
        log_admin_action(callback_query.from_user.id, "admin_health", "Health-check из админ-панели")
        await callback_query.message.reply_text(get_health_text())

    elif data == "admin_logs":
        await callback_query.answer("Готово")
        log_admin_action(callback_query.from_user.id, "admin_logs", "Просмотр admin logs из админ-панели")
        await callback_query.message.reply_text(get_admin_logs_text())

    elif data == "admin_export_users":
        await callback_query.answer("Готовлю файл")
        file_path, rows_count = create_users_export()
        log_admin_action(callback_query.from_user.id, "export_users", f"Экспортировано пользователей: {rows_count}")

        await send_csv_file(
            client,
            callback_query.message.chat.id,
            file_path,
            f"📥 Экспорт пользователей\n\nЗаписей: {rows_count}"
        )

    elif data == "admin_export_feedback":
        await callback_query.answer("Готовлю файл")
        file_path, rows_count = create_feedback_export()
        log_admin_action(callback_query.from_user.id, "export_feedback", f"Экспортировано feedback: {rows_count}")

        await send_csv_file(
            client,
            callback_query.message.chat.id,
            file_path,
            f"💬 Экспорт обратной связи\n\nЗаписей: {rows_count}"
        )

    elif data == "admin_last_feedback":
        await callback_query.answer("Готово")
        log_admin_action(callback_query.from_user.id, "last_feedback", "Просмотр последних feedback")
        await callback_query.message.reply_text(get_last_feedback_text())

    elif data == "admin_backup_db":
        await callback_query.answer("Готовлю backup")
        log_admin_action(callback_query.from_user.id, "backup_db", "Backup базы из админ-панели")

        if not os.path.exists(DB_PATH):
            await callback_query.message.reply_text("⚠️ Файл базы данных пока не найден.")
            return

        await client.send_document(
            callback_query.message.chat.id,
            DB_PATH,
            caption="🗄 Резервная копия базы данных"
        )

    elif data == "admin_test_notify":
        await callback_query.answer("Отправляю тест")
        log_admin_action(callback_query.from_user.id, "test_notify", "Тест уведомления из админ-панели")
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
            f"Максимальная длина: {MAX_BROADCAST_LENGTH} символов.\n\n"
            "Пример:\n"
            "`/broadcast Привет! Я обновил бота 🚀`"
        )

    elif data == "admin_reply_help":
        await callback_query.answer("Инструкция")
        await callback_query.message.reply_text(
            "💬 Ответ пользователю\n\n"
            "Используй команду:\n"
            "`/reply user_id текст ответа`\n\n"
            f"Максимальная длина: {MAX_REPLY_LENGTH} символов.\n\n"
            "Пример:\n"
            "`/reply 123456789 Привет! Спасибо за сообщение.`"
        )

    else:
        await callback_query.answer("Неизвестное действие", show_alert=False)


@app.on_message(filters.command("test_notify"))
@handle_errors
async def test_notify_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    log_admin_action(message.from_user.id, "test_notify", "Тест уведомления через команду")
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

    wait_seconds = get_feedback_wait_seconds(message.from_user.id)

    if wait_seconds > 0:
        await message.reply_text(
            "⏳ Не так быстро.\n\n"
            f"Следующее сообщение можно отправить через {wait_seconds} сек."
        )
        return

    feedback_text = message.text.split(maxsplit=1)[1].strip()

    if not feedback_text:
        await message.reply_text("⚠️ Сообщение не должно быть пустым.")
        return

    if len(feedback_text) > MAX_FEEDBACK_LENGTH:
        await message.reply_text(
            "⚠️ Сообщение слишком длинное.\n\n"
            f"Максимум: {MAX_FEEDBACK_LENGTH} символов.\n"
            f"Сейчас: {len(feedback_text)} символов."
        )
        return

    ensure_user_record(message.from_user)
    save_feedback(message.from_user, feedback_text)

    await notify_admin_about_feedback(client, message.from_user, feedback_text)

    await message.reply_text(
        "✅ Сообщение отправлено автору бота.\n"
        "Спасибо за обратную связь!"
    )


@app.on_message(filters.command("reply"))
@handle_errors
async def reply_command(client, message):
    if not is_admin_user_id(message.from_user.id):
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

    reply_text = parts[2].strip()

    if not reply_text:
        await message.reply_text("⚠️ Текст ответа не должен быть пустым.")
        return

    if len(reply_text) > MAX_REPLY_LENGTH:
        await message.reply_text(
            "⚠️ Ответ слишком длинный.\n\n"
            f"Максимум: {MAX_REPLY_LENGTH} символов."
        )
        return

    try:
        await client.send_message(
            target_user_id,
            "💬 Ответ от автора бота:\n\n"
            f"{reply_text}"
        )
        log_admin_action(
            message.from_user.id,
            "reply",
            f"Ответ пользователю {target_user_id}: {truncate_text(reply_text, 250)}"
        )
        await message.reply_text("✅ Ответ отправлен пользователю.")
    except Exception as error:
        await message.reply_text(f"⚠️ Не удалось отправить ответ: {error}")


@app.on_message(filters.command("backup_db"))
@handle_errors
async def backup_db_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    if not os.path.exists(DB_PATH):
        await message.reply_text("⚠️ Файл базы данных пока не найден.")
        return

    log_admin_action(message.from_user.id, "backup_db", "Backup базы через команду")

    await client.send_document(
        message.chat.id,
        DB_PATH,
        caption="🗄 Резервная копия базы данных"
    )


@app.on_message(filters.command("last_feedback"))
@handle_errors
async def last_feedback_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    log_admin_action(message.from_user.id, "last_feedback", "Просмотр последних feedback через команду")
    await message.reply_text(get_last_feedback_text())


@app.on_message(filters.command("admin_logs"))
@handle_errors
async def admin_logs_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    log_admin_action(message.from_user.id, "admin_logs", "Просмотр admin logs через команду")
    await message.reply_text(get_admin_logs_text())


@app.on_message(filters.command("export_users"))
@handle_errors
async def export_users_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    file_path, rows_count = create_users_export()
    log_admin_action(message.from_user.id, "export_users", f"Экспортировано пользователей: {rows_count}")

    await send_csv_file(
        client,
        message.chat.id,
        file_path,
        f"📥 Экспорт пользователей\n\nЗаписей: {rows_count}"
    )


@app.on_message(filters.command("export_feedback"))
@handle_errors
async def export_feedback_command(client, message):
    if not is_admin_user_id(message.from_user.id):
        await message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    file_path, rows_count = create_feedback_export()
    log_admin_action(message.from_user.id, "export_feedback", f"Экспортировано feedback: {rows_count}")

    await send_csv_file(
        client,
        message.chat.id,
        file_path,
        f"💬 Экспорт обратной связи\n\nЗаписей: {rows_count}"
    )


@app.on_message(filters.command("broadcast"))
@handle_errors
async def broadcast_command(client, message):
    if not is_admin_user_id(message.from_user.id):
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

    broadcast_text = message.text.split(maxsplit=1)[1].strip()

    if not broadcast_text:
        await message.reply_text("⚠️ Текст рассылки не должен быть пустым.")
        return

    if len(broadcast_text) > MAX_BROADCAST_LENGTH:
        await message.reply_text(
            "⚠️ Текст рассылки слишком длинный.\n\n"
            f"Максимум: {MAX_BROADCAST_LENGTH} символов."
        )
        return

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
            await asyncio.sleep(0.05)

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

    log_admin_action(
        message.from_user.id,
        "broadcast",
        f"Отправлено: {sent_count}, ошибок: {failed_count}, текст: {truncate_text(broadcast_text, 250)}"
    )

    await message.reply_text(
        "✅ Рассылка завершена\n\n"
        f"Отправлено: {sent_count}\n"
        f"Ошибок: {failed_count}"
    )


@app.on_message(
    filters.text
    & filters.private
    & ~filters.command(ALL_COMMANDS + ["me"])
)
@handle_errors
async def menu(client, message):
    text = message.text

    if text == "👨‍💻 Обо мне":
        await message.reply_text(
            "👨‍💻 Обо мне\n\n"
            "Привет! Меня зовут Freedomfall.\n"
            "Я изучаю Python и создаю Telegram-ботов.\n\n"
            "Этот бот — мой проект для портфолио: он уже умеет работать "
            "со статистикой, базой данных, админ-панелью, логами, рассылкой "
            "и обратной связью."
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
            "• Основы backend-разработки\n"
            "• Обработка ошибок\n"
            "• Антиспам и лимиты\n"
            "• Админ-панель и CSV-экспорт"
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
        await message.reply_text(get_about_project_text())

    elif text == "💬 Связаться":
        await message.reply_text(
            "💬 Связаться со мной\n\n"
            "Напиши сообщение командой:\n\n"
            "`/feedback твой текст`\n\n"
            f"Максимальная длина: {MAX_FEEDBACK_LENGTH} символов.\n\n"
            "Пример:\n"
            "`/feedback Привет! Хочу обсудить Telegram-бота.`"
        )

    elif text == "🚀 Версия":
        await message.reply_text(get_version_text())

    elif text == "🧭 Roadmap":
        await message.reply_text(get_roadmap_text())

    elif text == "🔐 Privacy":
        await message.reply_text(get_privacy_text())

    elif text == "🪙 Монетка":
        await send_coin_animation(message)

    elif text == "🎲 Кубик":
    	await send_dice_animation(message)

    elif text == "👤 Профиль":
        await message.reply_text(get_profile_text(message.from_user))

    elif text == "📊 Статистика":
        if not is_admin_user_id(message.from_user.id):
            await message.reply_text("⛔ У тебя нет доступа к статистике.")
            return

        log_admin_action(message.from_user.id, "stats_button", "Статистика через кнопку меню")
        await message.reply_text(get_stats_text())

    elif text == "❓ Помощь":
        await message.reply_text(
            get_help_text(),
            reply_markup=keyboard
        )

    else:
        await message.reply_text(
            "Я пока не понимаю это сообщение 😅\n"
            "Нажми одну из кнопок ниже или используй команду /help.",
            reply_markup=keyboard
        )


init_db()
app.run()

import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client(
    "portfolio_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

keyboard = ReplyKeyboardMarkup(
    [
        ["👨‍💻 Обо мне", "🛠 Навыки"],
        ["📂 Проекты", "📬 Контакты"]
    ],
    resize_keyboard=True
)


@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "Привет! 👋\n\n"
        "Я портфолио-бот начинающего Python-разработчика.\n"
        "Выбери раздел ниже:",
        reply_markup=keyboard
    )


@app.on_message(filters.text & filters.private)
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
            "• Основы баз данных"
        )

    elif text == "📂 Проекты":
        await message.reply_text(
            "📂 Мои проекты\n\n"
            "1. Portfolio Bot — бот-визитка в Telegram\n"
            "2. Todo Bot — бот для задач, скоро\n"
            "3. Weather Bot — бот погоды, скоро"
        )

    elif text == "📬 Контакты":
        await message.reply_text(
            "📬 Контакты\n\n"
            "Telegram: @freedomfall\n"
            "GitHub: https://github.com/Freedomfall\n"
            "Email: upvake@gmail.com",
            reply_markup=InlineKeyboardMarkup(
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
                    ]
                ]
            )
        )

    else:
        await message.reply_text(
            "Я пока не понимаю эту команду 😅\n"
            "Нажми одну из кнопок ниже.",
            reply_markup=keyboard
        )


app.run()
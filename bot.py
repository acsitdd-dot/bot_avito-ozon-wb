"""
Telegram-бот "Навигация после покупки курса"
=============================================

Что делает:
- По команде /start (и по кнопке "Меню") показывает 4 кнопки-раздела:
  1. Сайт
  2. Телеграм-канал
  3. Чат единомышленников
  4. AI-ассистент

Сейчас все 4 пункта — просто ссылки-заглушки (LINKS ниже).
Меняете их на реальные, когда разделы будут готовы — код трогать не нужно.

Как запустить:
1. Установите библиотеку:
   pip install python-telegram-bot --break-system-packages   (или без флага, если у вас обычный Python)

2. Получите токен бота:
   - Откройте Telegram, напишите @BotFather
   - Команда /newbot, следуйте инструкции
   - Скопируйте токен вида 123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

3. Вставьте токен в переменную BOT_TOKEN ниже (или задайте переменную окружения BOT_TOKEN).

4. Запустите:
   python bot.py

Бот будет работать, пока запущен этот процесс. Чтобы он работал 24/7,
его нужно разместить на сервере/VPS или на сервисе типа Railway/Render.
Скажите — помогу с этим шагом отдельно, когда дойдёте до него.
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ЗАПОЛНИТЕ ЭТО ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬТЕ_СЮДА_ТОКЕН_ОТ_BOTFATHER")

# Заглушки-ссылки на 4 раздела. Как будут готовы — просто замените адреса.
LINKS = {
    "site": "https://neon-crepe-6a8362.netlify.app/",                 # 1. Сайт (пока не сделан)
    "channel": "https://t.me/rejug9rgjb9re495",    # 2. Телеграм-канал
    "chat": "https://t.me/jgeierethg985989",          # 3. Чат единомышленников
    "ai": "https://t.me/AvitOzonWb1_bot",          # 4. AI-ассистент
}

WELCOME_TEXT = (
    "Добро пожаловать! 👋\n\n"
    "Здесь собраны все материалы курса. Выберите раздел:"
)

# ==========================================================================


def build_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🌐 Сайт", url=LINKS["site"])],
        [InlineKeyboardButton("📢 Телеграм-канал (уроки, посты, видео)", url=LINKS["channel"])],
        [InlineKeyboardButton("💬 Чат единомышленников", url=LINKS["chat"])],
        [InlineKeyboardButton("🤖 AI-ассистент", url=LINKS["ai"])],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, reply_markup=build_menu())


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Позволяет вызвать меню повторно командой /menu"""
    await update.message.reply_text("Меню разделов:", reply_markup=build_menu())


def main() -> None:
    if "ВСТАВЬТЕ_СЮДА" in BOT_TOKEN:
        print("⚠️  Не забудьте вставить свой токен в переменную BOT_TOKEN (см. инструкцию вверху файла).")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))

    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()

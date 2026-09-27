"""
AI-ассистент для консультаций по продвижению на Авито/WB/Ozon
================================================================
Версия на OpenRouter (модель Google Gemini 2.0 Flash Lite)
С поддержкой анализа фотографий карточек товаров и разбивкой длинных сообщений.
"""

import base64
import logging
import os
from openai import OpenAI
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================================================
# Читаем ключи из переменных окружения (Railway Variables)
# ==========================================================================

BOT_TOKEN = os.environ.get("AI_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Выбираем мультимодальную модель (умеет читать и текст, и картинки)
MODEL = "google/gemini-2.0-flash-lite-001:free"

SYSTEM_PROMPT = """
Ты — AI-консультант по продвижению на маркетплейсах (Авито, Wildberries, Ozon).
Ты помогаешь ученикам курса разобраться с их объявлениями/карточками товаров.

Твоя методика аудита (используй её как основу для советов):
1. Заголовок — есть ли ключевые слова, длина, чёткое УТП
2. Фото/видео — качество, количество, обложка (первое фото цепляет?)
3. Цена — сравнение с конкурентами в нише (не завышена/не занижена)
4. Описание — структура, закрытие болей клиента, призыв к действию
5. Скорость ответа в чате — влияет на ранжирование
6. Платное продвижение — используется ли поднятие/XL-объявление
7. Отзывы и рейтинг — есть ли, как собирать
8. Категория/раздел/география — правильно ли выбраны

Правила общения:
- Отвечай конкретно и по делу, без общих фраз "все индивидуально"
- Если ученик прислал фото карточки — подробно проанализируй обложку, инфографику и дизайн
- Задавай уточняющие вопросы, если информации мало
- Не выдумывай цифры и статистику, которых не знаешь
- Тон — как у опытного наставника: дружелюбно, но без "воды"
"""

HISTORY_LIMIT = 12
MAX_MESSAGE_LENGTH = 4000  # Лимит символов на одно сообщение в Telegram

# Инициализация клиента OpenAI для работы через шлюз OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

history: dict[int, list[dict]] = {}

# Клавиатура с удобными кнопками управления
reply_markup = ReplyKeyboardMarkup([["/start", "/reset"]], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    history[chat_id] = []
    await update.message.reply_text(
        "Привет! Я AI-консультант по продвижению на Авито/WB/Ozon.\n\n"
        "Пришлите текст вашего объявления, фото карточки "
        "или конкретный вопрос — разберу и дам рекомендации.\n\n"
        "Воспользуйтесь кнопками ниже для управления.",
        reply_markup=reply_markup,
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history[update.effective_chat.id] = []
    await update.message.reply_text(
        "Диалог сброшен. Пишите новый вопрос.", reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = (
        update.message.text
        or update.message.caption
        or "Проанализируй это изображение."
    )

    # Формируем структуру сообщения (поддержка текста и мультимедиа)
    message_content = [{"type": "text", "text": user_text}]

    # Если пользователь прислал фото
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        base64_image = base64.b64encode(photo_bytes).decode("utf-8")
        message_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        })

    chat_history = history.setdefault(chat_id, [])
    chat_history.append({"role": "user", "content": message_content})
    chat_history[:] = chat_history[-HISTORY_LIMIT:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}]
            + chat_history,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        logger.exception("Ошибка обращения к OpenRouter API")
        answer = (
            "Не получилось получить ответ от AI (техническая ошибка). "
            "Попробуйте ещё раз через минуту."
        )

    # Сохраняем полученный ответ в историю
    chat_history.append({"role": "assistant", "content": str(answer)})

    # Делим слишком длинный ответ на фрагменты до 4000 символов
    for i in range(0, len(answer), MAX_MESSAGE_LENGTH):
        await update.message.reply_text(
            answer[i : i + MAX_MESSAGE_LENGTH], reply_markup=reply_markup
        )


def main() -> None:
    if not BOT_TOKEN:
        print("⚠️ Ошибка: не задана переменная окружения AI_BOT_TOKEN!")
        return
    if not OPENROUTER_API_KEY:
        print("⚠️ Ошибка: не задана переменная окружения OPENROUTER_API_KEY!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))

    # Принимаем и текстовые сообщения, и фото
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message
        )
    )

    print("AI-ассистент запущен и готов к работе.")
    app.run_polling()


if __name__ == "__main__":
    main()

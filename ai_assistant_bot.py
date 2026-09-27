import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ЗАПОЛНИТЕ ЭТО ============================================================

BOT_TOKEN = os.environ.get("AI_BOT_TOKEN", "ВСТАВЬТЕ_СЮДА_ТОКЕН_ЭТОГО_БОТА")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "ВСТАВЬТЕ_СЮДА_КЛЮЧ_GROQ")

MODEL = "openai/gpt-oss-20b"  # подтверждено вашим ключом

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
- Если ученик прислал ссылку на объявление, а ты не можешь её открыть —
  честно скажи, что не видишь содержимое по ссылке, и попроси прислать
  текст заголовка/описания/цену вручную
- Задавай уточняющие вопросы, если информации мало
- Не выдумывай цифры и статистику, которых не знаешь
- Тон — как у опытного наставника: дружелюбно, но без "воды"
- Если вопрос выходит за рамки маркетплейсов (личные проблемы,
  медицина, юридические споры и т.п.) — вежливо скажи, что это не твоя
  специализация, и посоветуй обратиться к профильному специалисту
"""

HISTORY_LIMIT = 12
MAX_MESSAGE_LENGTH = 4000  # Лимит символов для отправки в Telegram

# ==========================================================================

client = Groq(api_key=GROQ_API_KEY)
history: dict[int, list[dict]] = {}

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🔄 Сбросить диалог"), KeyboardButton("ℹ️ Помощь")]
    ]
    # Исправлено: в python-telegram-bot аргумент называется is_persistent
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    history[chat_id] = []
    
    welcome_text = (
        "Привет! Я AI-консультант по продвижению на Авито/WB/Ozon.\n\n"
        "Пришлите текст вашего объявления (заголовок, описание, цену) "
        "или задайте конкретный вопрос — разберу и дам рекомендации.\n\n"
        "Используйте кнопки ниже или команду /reset для сброса диалога."
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    history[chat_id] = []
    await update.message.reply_text(
        "Диалог сброшен. Пишите новый вопрос.", 
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "💡 <b>Как пользоваться ботом:</b>\n\n"
        "1. Отправьте текст объявления, карточки или опишите вашу проблему с продажами.\n"
        "2. Бот проанализирует данные по методике (заголовок, фото, цена, описание и др.).\n"
        "3. Нажмите кнопку <b>🔄 Сбросить диалог</b>, чтобы начать консультацию с чистого листа."
    )
    await update.message.reply_text(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Обработка нажатий на текстовые кнопки с клавиатуры
    if user_text == "🔄 Сбросить диалог":
        return await reset(update, context)
    elif user_text == "ℹ️ Помощь":
        return await help_command(update, context)

    chat_history = history.setdefault(chat_id, [])
    chat_history.append({"role": "user", "content": user_text})
    chat_history[:] = chat_history[-HISTORY_LIMIT:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1500,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        logger.exception("Ошибка обращения к Groq API")
        answer = (
            "Не получилось получить ответ от AI (техническая ошибка). "
            "Попробуйте ещё раз через минуту."
        )

    # Принудительное ограничение по длине в символах для Telegram (4096 макс)
    if len(answer) > MAX_MESSAGE_LENGTH:
        answer = answer[:MAX_MESSAGE_LENGTH] + "\n\n...(ответ сокращен из-за лимита Telegram)"

    chat_history.append({"role": "assistant", "content": answer})
    
    await update.message.reply_text(answer, reply_markup=get_main_keyboard())


def main() -> None:
    if "ВСТАВЬТЕ_СЮДА" in BOT_TOKEN or "ВСТАВЬТЕ_СЮДА" in GROQ_API_KEY:
        print("⚠️ Заполните BOT_TOKEN и GROQ_API_KEY перед запуском (см. инструкцию вверху файла).")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("AI-ассистент запущен с кнопками и лимитом сообщений. Нажмите Ctrl+C для остановки.")
    # drop_pending_updates=True сбрасывает старые зависшие запросы при перезапуске на Railway
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

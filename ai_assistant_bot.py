"""
AI-ассистент для консультаций по продвижению на Авито/WB/Ozon
================================================================
Версия на Groq — БЕСПЛАТНЫЙ API (в отличие от Anthropic).

Отдельный Telegram-бот. Клиент пишет ему вопрос ("почему мало просмотров",
"как оформить карточку" и т.д.) — бот отвечает как консультант, опираясь
на встроенную методику аудита (см. SYSTEM_PROMPT ниже).

Это и есть пункт "4. AI-ассистент" из общей навигации (bot.py).
Когда получите этого бота от @BotFather — вставьте его @username
в LINKS["ai"] в файле bot.py.

Что нужно для запуска:
1. Установить библиотеки:
   python -m pip install python-telegram-bot groq

2. Получить токен ЭТОГО бота у @BotFather (это ДРУГОЙ бот, отдельный
   от навигационного) — команда /newbot, скопировать токен.

3. Получить БЕСПЛАТНЫЙ ключ Groq:
   - Зайти на https://console.groq.com/keys
   - Войти (через Google-аккаунт можно) -> Create API Key
   - Никакой карты и оплаты не требуется на момент написания кода

4. Вставить оба значения ниже (BOT_TOKEN и GROQ_API_KEY)
   или задать их как переменные окружения с теми же именами.

5. Запуск:
   python ai_assistant_bot.py

Важно: бесплатные лимиты Groq (сколько запросов в минуту/день) со временем
меняются — если бот начнёт отвечать ошибкой "rate limit", проверьте текущие
лимиты на https://console.groq.com/settings/limits
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ЗАПОЛНИТЕ ЭТО ============================================================

BOT_TOKEN = os.environ.get("AI_BOT_TOKEN", "ВСТАВЬТЕ_СЮДА_ТОКЕН_ЭТОГО_БОТА")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "ВСТАВЬТЕ_СЮДА_КЛЮЧ_GROQ")

MODEL = "openai/gpt-oss-20b"  # подтверждено вашим ключом через check_groq_models.py

# Проверено 26.09.2026 запросом к /v1/models — модель реально доступна.
# Если Groq снова изменит список, запустите check_groq_models.py ещё раз
# и возьмите любую строку без "whisper", "prompt-guard", "orpheus" (это не
# чат-модели, а речь/безопасность/голос).

# Здесь — ваша методика. Отредактируйте под себя: чем подробнее, тем точнее
# будут ответы бота. Это как раз то, что вы объясняете клиентам вручную —
# сейчас это делает бот 24/7.
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

# Сколько последних сообщений помнить в рамках диалога с одним пользователем
HISTORY_LIMIT = 12

# ==========================================================================

client = Groq(api_key=GROQ_API_KEY)

# Простая память в оперативной памяти процесса: {chat_id: [сообщения]}
# При перезапуске бота история обнуляется. Для продакшена лучше вынести
# в БД (Redis/SQLite) — скажите, если нужно это добавить.
history: dict[int, list[dict]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    history[chat_id] = []
    await update.message.reply_text(
        "Привет! Я AI-консультант по продвижению на Авито/WB/Ozon.\n\n"
        "Пришлите текст вашего объявления (заголовок, описание, цену) "
        "или конкретный вопрос — разберу и дам рекомендации.\n\n"
        "Команда /reset — начать диалог заново."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history[update.effective_chat.id] = []
    await update.message.reply_text("Диалог сброшен. Пишите новый вопрос.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text

    chat_history = history.setdefault(chat_id, [])
    chat_history.append({"role": "user", "content": user_text})
    chat_history[:] = chat_history[-HISTORY_LIMIT:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        logger.exception("Ошибка обращения к Anthropic API")
        answer = (
            "Не получилось получить ответ от AI (техническая ошибка). "
            "Попробуйте ещё раз через минуту."
        )

    chat_history.append({"role": "assistant", "content": answer})
    await update.message.reply_text(answer)


def main() -> None:
    if "ВСТАВЬТЕ_СЮДА" in BOT_TOKEN or "ВСТАВЬТЕ_СЮДА" in GROQ_API_KEY:
        print("⚠️  Заполните BOT_TOKEN и GROQ_API_KEY перед запуском (см. инструкцию вверху файла).")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("AI-ассистент запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()

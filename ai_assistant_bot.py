"""
AI-ассистент для консультаций по продвижению на Авито/WB/Ozon
================================================================
Версия на Groq — БЕСПЛАТНЫЙ API (в отличие от Anthropic).[cite: 1]

Отдельный Telegram-бот. Клиент пишет ему вопрос ("почему мало просмотров",
"как оформить карточку" и т.д.) — бот отвечает как консультант, опираясь
на встроенную методику аудита (см. SYSTEM_PROMPT ниже).[cite: 1]

Это и есть пункт "4. AI-ассистент" из общей навигации (bot.py).[cite: 1]
Когда получите этого бота от @BotFather — вставьте его @username
в LINKS["ai"] в файле bot.py.[cite: 1]

Что нужно для запуска:
1. Установить библиотеки:
   python -m pip install python-telegram-bot groq[cite: 1]

2. Получить токен ЭТОГО бота у @BotFather (это ДРУГОЙ бот, отдельный
   от навигационного) — команда /newbot, скопировать токен.[cite: 1]

3. Получить БЕСПЛАТНЫЙ ключ Groq:
   - Зайти на https://console.groq.com/keys[cite: 1]
   - Войти (через Google-аккаунт можно) -> Create API Key[cite: 1]
   - Никакой карты и оплаты не требуется на момент написания кода[cite: 1]

4. Вставить оба значения ниже (BOT_TOKEN и GROQ_API_KEY)
   или задать их как переменные окружения с теми же именами.[cite: 1]

5. Запуск:
   python ai_assistant_bot.py[cite: 1]

Важно: бесплатные лимиты Groq (сколько запросов в минуту/день) со временем
меняются — если бот начнёт отвечать ошибкой "rate limit", проверьте текущие
лимиты на https://console.groq.com/settings/limits[cite: 1]
"""

import os
import logging
import base64
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from groq import Groq

logging.basicConfig(level=logging.INFO)[cite: 1]
logger = logging.getLogger(__name__)[cite: 1]

# ЗАПОЛНИТЕ ЭТО ============================================================

BOT_TOKEN = os.environ.get("AI_BOT_TOKEN", "ВСТАВЬТЕ_СЮДА_ТОКЕН_ЭТОГО_БОТА")[cite: 1]
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "ВСТАВЬТЕ_СЮДА_КЛЮЧ_GROQ")[cite: 1]

# Используем модель с поддержкой Vision (анализ изображений)
MODEL = "llama-3.2-11b-vision-preview"

# Здесь — ваша методика. Отредактируйте под себя: чем подробнее, тем точнее
# будут ответы бота. Это как раз то, что вы объясняете клиентам вручную —
# сейчас это делает бот 24/7.[cite: 1]
SYSTEM_PROMPT = """
Ты — AI-консультант по продвижению на маркетплейсах (Авито, Wildberries, Ozon).[cite: 1]
Ты помогаешь ученикам курса разобраться с их объявлениями/карточками товаров.[cite: 1]

Твоя методика аудита (используй её как основу для советов):
1. Заголовок — есть ли ключевые слова, длина, чёткое УТП[cite: 1]
2. Фото/видео — качество, количество, обложка (первое фото цепляет?)[cite: 1]
3. Цена — сравнение с конкурентами в нише (не завышена/не занижена)[cite: 1]
4. Описание — структура, закрытие болей клиента, призыв к действию[cite: 1]
5. Скорость ответа в чате — влияет на ранжирование[cite: 1]
6. Платное продвижение — используется ли поднятие/XL-объявление[cite: 1]
7. Отзывы и рейтинг — есть ли, как собирать[cite: 1]
8. Категория/раздел/география — правильно ли выбраны[cite: 1]

Правила общения:
- Отвечай конкретно и по делу, без общих фраз "все индивидуально"[cite: 1]
- Если ученик прислал ссылку на объявление, а ты не можешь её открыть —
  честно скажи, что не видишь содержимое по ссылке, и попроси прислать
  текст заголовка/описания/цену вручную[cite: 1]
- Задавай уточняющие вопросы, если информации мало[cite: 1]
- Не выдумывай цифры и статистику, которых не знаешь[cite: 1]
- Тон — как у опытного наставника: дружелюбно, но без "воды"[cite: 1]
- Если вопрос выходит за рамки маркетплейсов (личные проблемы,
  медицина, юридические споры и т.п.) — вежливо скажи, что это не твоя
  специализация, и посоветуй обратиться к профильному специалисту[cite: 1]
"""

# Сколько последних сообщений помнить в рамках диалога с одним пользователем[cite: 1]
HISTORY_LIMIT = 12[cite: 1]
MAX_MESSAGE_LENGTH = 4000  # Безопасный лимит символов для отправки в Telegram

# ==========================================================================

client = Groq(api_key=GROQ_API_KEY)[cite: 1]

# Простая память в оперативной памяти процесса: {chat_id: [сообщения]}[cite: 1]
# При перезапуске бота история обнуляется. Для продакшена лучше вынести[cite: 1]
# в БД (Redis/SQLite) — скажите, если нужно это добавить.[cite: 1]
history: dict[int, list[dict]] = {}[cite: 1]

# Клавиатура с кнопками управления
reply_markup = ReplyKeyboardMarkup([['/start', '/reset']], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:[cite: 1]
    chat_id = update.effective_chat.id[cite: 1]
    history[chat_id] = [][cite: 1]
    await update.message.reply_text(
        "Привет! Я AI-консультант по продвижению на Авито/WB/Ozon.\n\n"[cite: 1]
        "Пришлите текст вашего объявления, фото карточки "
        "или конкретный вопрос — разберу и дам рекомендации.\n\n"
        "Воспользуйтесь кнопками ниже для управления.",
        reply_markup=reply_markup
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:[cite: 1]
    history[update.effective_chat.id] = [][cite: 1]
    await update.message.reply_text("Диалог сброшен. Пишите новый вопрос.", reply_markup=reply_markup)[cite: 1]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:[cite: 1]
    chat_id = update.effective_chat.id[cite: 1]
    user_text = update.message.text or update.message.caption or "Посмотри на это фото."

    # Подготовка контента для отправки (текст или текст + фото)
    message_content = [{"type": "text", "text": user_text}]

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        message_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    chat_history = history.setdefault(chat_id, [])[cite: 1]
    chat_history.append({"role": "user", "content": message_content})
    chat_history[:] = chat_history[-HISTORY_LIMIT:][cite: 1]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")[cite: 1]

    try:
        response = client.chat.completions.create([cite: 1]
            model=MODEL,[cite: 1]
            max_tokens=2000,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history,[cite: 1]
        )[cite: 1]
        answer = response.choices[0].message.content[cite: 1]
    except Exception as e:
        logger.exception("Ошибка обращения к Groq API")
        answer = (
            "Не получилось получить ответ от AI (техническая ошибка). "[cite: 1]
            "Попробуйте ещё раз через минуту."[cite: 1]
        )

    # Сохраняем текстовый ответ в историю для правильного контекста
    chat_history.append({"role": "assistant", "content": str(answer)})

    # Отправка длинных сообщений частями для обхода лимита Telegram в 4096 символов
    for i in range(0, len(answer), MAX_MESSAGE_LENGTH):
        await update.message.reply_text(answer[i:i + MAX_MESSAGE_LENGTH], reply_markup=reply_markup)


def main() -> None:[cite: 1]
    if "ВСТАВЬТЕ_СЮДА" in BOT_TOKEN or "ВСТАВЬТЕ_СЮДА" in GROQ_API_KEY:[cite: 1]
        print("⚠️  Заполните BOT_TOKEN и GROQ_API_KEY перед запуском (см. инструкцию вверху файла).")[cite: 1]
        return[cite: 1]

    app = Application.builder().token(BOT_TOKEN).build()[cite: 1]
    app.add_handler(CommandHandler("start", start))[cite: 1]
    app.add_handler(CommandHandler("reset", reset))[cite: 1]
    
    # Обработка как текста, так и фото
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

    print("AI-ассистент запущен. Нажмите Ctrl+C для остановки.")[cite: 1]
    app.run_polling()[cite: 1]


if __name__ == "__main__":[cite: 1]
    main()[cite: 1]

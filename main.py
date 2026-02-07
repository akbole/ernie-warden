import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
# 👇 НОВАЯ СТРОКА (ПРАВИЛЬНО)
DB_NAME = "/data/bot_database.db" 
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")  # токен берётся из Render Environment

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Environment Variables")

# =========================
# ФЕЙКОВЫЙ HTTP СЕРВЕР (ДЛЯ RENDER)
# =========================

def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👀 Осмотреться", callback_data="look")]
    ]

    await update.message.reply_text(
        "🔌 Соединение установлено.\n\n"
        "Не переживай. Ты ничего не сломал.\n"
        "Ты находишься в Лобби.\n\n"
        "Что будешь делать?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# КНОПКИ
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "look":
        keyboard = [
            [InlineKeyboardButton("🚪 Подойти к лифту", callback_data="elevator")]
        ]

        await query.edit_message_text(
            "Ты осматриваешься.\n\n"
            "Бетонные стены.\n"
            "Пластиковый стул.\n"
            "Ощущение, что тебя оценивают.\n\n"
            "Система шепчет:\n"
            "«Не трать ресурсы зря».",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "elevator":
        keyboard = [
            [InlineKeyboardButton("🧠 Выполнить задание", callback_data="work")]
        ]

        await query.edit_message_text(
            "Ты подходишь к лифту.\n\n"
            "🚫 ДОСТУП ЗАПРЕЩЁН\n\n"
            "Требуется уровень доверия: 50%\n"
            "Текущий уровень: 5%\n\n"
            "Хочешь поработать?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "work":
        await query.edit_message_text(
            "🧪 Задача принята.\n"
            "📊 Анализ данных...\n\n"
            "Эрни: «Терпение — тоже навык».\n\n"
            "✅ Доверие +1%"
        )


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":
    # запускаем HTTP сервер для Render
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # запускаем Telegram-бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("🟢 WARDEN ONLINE")
    app.run_polling()

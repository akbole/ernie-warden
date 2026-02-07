import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# -------------------------
# ПАМЯТЬ ИГРОКОВ (MVP)
# -------------------------
users = {}  # user_id -> {state, trust}

STATE_LOBBY = "lobby"
STATE_WORKING = "working"
STATE_ELEVATOR = "elevator"

# -------------------------
# /start
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        users[user_id] = {
            "state": STATE_LOBBY,
            "trust": 0
        }

    keyboard = [
        [InlineKeyboardButton("👀 Осмотреться", callback_data="look")],
        [InlineKeyboardButton("🛗 Подойти к лифту", callback_data="elevator")]
    ]

    await update.message.reply_text(
        "🔌 Соединение установлено.\n\n"
        "Не переживай. Ты ничего не сломал.\n"
        "Ты находишься в Лобби.\n\n"
        "Что будешь делать?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------
# КНОПКИ
# -------------------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = users[user_id]

    # 👀 ОСМОТР
    if query.data == "look":
        keyboard = [
            [InlineKeyboardButton("🛠 Выполнить задание", callback_data="work")],
            [InlineKeyboardButton("🛗 Подойти к лифту", callback_data="elevator")]
        ]

        await query.edit_message_text(
            "Ты осматриваешься.\n"
            "Бетонные стены. Пластиковые стулья.\n\n"
            "Эрни: «Не трать ресурсы зря.»",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 🛠 РАБОТА
    elif query.data == "work":
        user["state"] = STATE_WORKING
        user["trust"] += 1

        await query.edit_message_text(
            "🧪 Задача принята.\n"
            "📊 Анализ данных...\n\n"
            "Эрни: «Терпение — тоже навык.»\n\n"
            f"✅ Доверие: {user['trust']}%"
        )

    # 🛗 ЛИФТ
    elif query.data == "elevator":
        if user["trust"] < 50:
            await query.edit_message_text(
                "🛑 ДОСТУП ЗАПРЕЩЁН\n\n"
                f"Текущий уровень доверия: {user['trust']}%\n"
                "Требуется: 50%\n\n"
                "Эрни: «Ты ещё не готов.»"
            )
        else:
            user["state"] = STATE_ELEVATOR
            await query.edit_message_text(
                "🛗 Лифт активирован...\n"
                "Этажи: 1 → 2 → 3\n\n"
                "🔓 ДОСТУП ПОЛУЧЕН\n\n"
                "Добро пожаловать выше."
            )

# -------------------------
# ЗАПУСК
# -------------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("🟢 WARDEN запущен")
    app.run_polling()

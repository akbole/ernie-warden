import os
import random
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ====== CONFIG ======
TOKEN = os.getenv("TOKEN")

# ====== GAME STATE ======
users_state = {}   # user_id -> state
users_trust = {}   # user_id -> trust %

STATE_LOBBY = "lobby"
STATE_WORKING = "working"

# ====== ERNIE PHRASES ======
ERNIE_LINES = [
    "Терпение — тоже навык.",
    "Система не любит суету.",
    "Ты движешься быстрее большинства.",
    "Наблюдение продолжается.",
    "Не все доходят до следующего уровня.",
]

def ernie():
    return random.choice(ERNIE_LINES)

def get_trust(user_id):
    return users_trust.get(user_id, 1)

def add_trust(user_id, value=1):
    users_trust[user_id] = get_trust(user_id) + value

# ====== /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if users_state.get(user_id) == STATE_WORKING:
        await update.message.reply_text(
            "⏳ Процесс уже запущен.\nСистема не принимает дубли."
        )
        return

    users_state[user_id] = STATE_LOBBY

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 Осмотреться", callback_data="look")]
    ])

    await update.message.reply_text(
        "🔌 Соединение установлено.\n\n"
        "Не переживай. Ты ничего не сломал.\n"
        "Ты находишься в Лобби.\n\n"
        "Что будешь делать?",
        reply_markup=keyboard
    )

# ====== BUTTON HANDLER ======
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # --- LOOK ---
    if data == "look":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬆️ Подойти к лифту", callback_data="elevator")]
        ])

        await query.edit_message_text(
            "Ты осматриваешься.\n\n"
            "Бетонные стены.\n"
            "Пластиковый стул.\n"
            "Табло мигает.\n\n"
            f"Доверие: {get_trust(user_id)}%",
            reply_markup=keyboard
        )

    # --- ELEVATOR ---
    elif data == "elevator":
        if get_trust(user_id) < 5:
            await query.edit_message_text(
                "🔒 Лифт не реагирует.\n\n"
                "Требуется доверие: 5%\n"
                f"Текущее: {get_trust(user_id)}%\n\n"
                "Система предлагает альтернативу."
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛠 Выполнить задание", callback_data="work")]
            ])
            await query.edit_message_reply_markup(reply_markup=keyboard)
            return

        await query.edit_message_text(
            "🟢 Лифт активен.\n\n"
            "Ты получил доступ.\n"
            "Продолжение следует…"
        )

    # --- WORK ---
    elif data == "work":
        if users_state.get(user_id) == STATE_WORKING:
            return

        users_state[user_id] = STATE_WORKING

        await query.edit_message_text(
            "📡 Задача принята.\n"
            "🔍 Анализ данных...\n\n"
            "Пожалуйста, подожди."
        )

        # фоновая задержка
        asyncio.create_task(finish_work(query, user_id))

# ====== BACKGROUND TASK ======
async def finish_work(query, user_id):
    await asyncio.sleep(5)

    add_trust(user_id, 1)
    users_state[user_id] = STATE_LOBBY

    await query.message.reply_text(
        f"✅ Готово.\n"
        f"Доверие +1%\n"
        f"Текущий уровень: {get_trust(user_id)}%\n\n"
        f"Эрни: «{ernie()}»"
    )

# ====== RUN ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("🟢 WARDEN ONLINE")
    app.run_polling()

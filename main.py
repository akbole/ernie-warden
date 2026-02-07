import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")

# Путь к базе данных на диске Render
DB_NAME = "/data/bot_database.db" 

# Проверка токена
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Environment Variables Render!")

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            trust INTEGER DEFAULT 0,
            state TEXT DEFAULT 'lobby'
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT trust, state FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"trust": row[0], "state": row[1]}
    return {"trust": 0, "state": "lobby"}

def update_user(user_id, trust, state):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, trust, state) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET trust = excluded.trust, state = excluded.state
    ''', (user_id, trust, state))
    conn.commit()
    conn.close()

# Инициализируем базу при старте
init_db()

# --- ЛОГИКА БОТА ---
STATE_LOBBY = "lobby"
STATE_ELEVATOR = "elevator"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    keyboard = [
        [InlineKeyboardButton("👀 Осмотреться", callback_data="look")],
        [InlineKeyboardButton("🛗 Лифт", callback_data="elevator")]
    ]

    await update.message.reply_text(
        f"🔌 Система: Привет, {update.effective_user.first_name}.\n"
        f"Твоё доверие: {user['trust']}%\n\n"
        "Ты в Лобби. Что будешь делать?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    if query.data == "look":
        keyboard = [[InlineKeyboardButton("🛠 Работать (+1%)", callback_data="work")]]
        await query.edit_message_text(
            "Бетонные стены. Эрни наблюдает.\n\n"
            "Хочешь заработать доверие?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "work":
        new_trust = user['trust'] + 1
        update_user(user_id, new_trust, STATE_LOBBY)
        
        text = f"🧪 Задача выполнена.\n"
        if new_trust >= 50:
            text += "🎉 ТЫ ПРОШЕЛ ПРОВЕРКУ! Лифт открыт."
        else:
            text += f"Эрни: «Хорошо. Ещё {50 - new_trust}% до лифта.»"
        
        await query.edit_message_text(text)

    elif query.data == "elevator":
        if user['trust'] < 50:
            await query.edit_message_text(
                f"🛑 ДОСТУП ЗАПРЕЩЁН\n\n"
                f"Доверие: {user['trust']}% (Нужно 50%)\n\n"
                "Эрни: «Ты ещё не готов.»"
            )
        else:
            update_user(user_id, user['trust'], STATE_ELEVATOR)
            await query.edit_message_text(
                "🛗 Двери открываются...\n"
                "Ты входишь в лифт.\n\n"
                "Куда едем? (Пока тут пусто, но скоро будут этажи)"
            )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    print("🟢 WARDEN DB (Starter + Disk) запущен")
    app.run_polling()

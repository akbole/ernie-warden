import logging
import sqlite3
import json
import random
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ КОНФИГУРАЦИЯ (Из config.py)
# ==========================================
# Твой токен из BotFather
BOT_TOKEN = os.getenv('BOT_TOKEN', '7933434246:AAErOnLbmRoQrVWnwlnq_Wa7pWiYFAYE7P8')
DATABASE_NAME = 'ernie.db'
MAX_ENERGY = 10
ENERGY_RECOVERY_HOURS = 2
MAX_FLOORS = 100

# Ссылки на твои красивые картинки (Imgur)
LOCATION_IMAGES = {
    "bionic": "https://i.imgur.com/your_bionic_image.jpg", # Замени на свою прямую ссылку
    "bunker": "https://i.imgur.com/your_bunker_image.jpg"
}

# ==========================================
# 🎨 ТЕМЫ ЭТАЖЕЙ (Из floor_themes.py)
# ==========================================
FLOOR_THEMES = {
    "bunker": {"range": (1, 10), "name": "БЕТОННЫЙ БУНКЕР", "emoji": "🔧", "top": "╔════════════╗", "bot": "╚════════════╝"},
    "industrial": {"range": (11, 30), "name": "ПРОМЫШЛЕННЫЙ ЦЕХ", "emoji": "⚡", "top": "▬▬▬▬▬▬▬▬▬▬", "bot": "▬▬▬▬▬▬▬▬▬▬"},
    "laboratory": {"range": (31, 50), "name": "ЛАБОРАТОРИЯ", "emoji": "🔬", "top": "━━━━━━━━━━━━", "bot": "━━━━━━━━━━━━"},
    "cyberpunk": {"range": (51, 70), "name": "КИБЕРПАНК-ЛОФТ", "emoji": "🌃", "top": "┏━━━━━━━━━━━━┓", "bot": "┗━━━━━━━━━━━━┛"},
    "bionic": {"range": (71, 90), "name": "БИОНИЧЕСКИЙ САД", "emoji": "🌿", "top": "╭────────────╮", "bot": "╰────────────╯"},
    "transcendent": {"range": (91, 100), "name": "ТРАНСЦЕНДЕНТНОЕ", "emoji": "✨", "top": "════════════", "bot": "════════════"}
}

def get_theme(floor):
    for theme in FLOOR_THEMES.values():
        if theme["range"][0] <= floor <= theme["range"][1]: return theme
    return FLOOR_THEMES["transcendent"]

# ==========================================
# 📊 БАЗА ДАННЫХ (Из database.py)
# ==========================================
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, nickname TEXT, trust_level INTEGER DEFAULT 0,
        current_floor INTEGER DEFAULT 1, energy INTEGER DEFAULT 10,
        last_energy_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ernie_memory TEXT DEFAULT '{}', last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(user_id, nickname, first_choice):
    conn = sqlite3.connect(DATABASE_NAME)
    mem = json.dumps({'first_choice': first_choice, 'style': 'empathetic' if first_choice == 'read' else 'pragmatic'})
    conn.execute('INSERT INTO users (user_id, nickname, ernie_memory) VALUES (?, ?, ?)', (user_id, nickname, mem))
    conn.commit()
    conn.close()

# ==========================================
# 🤖 ЛОГИКА БОТА (Из main.py)
# ==========================================
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user:
        await update.message.reply_text(f"С возвращением, {user['nickname']}! Используй /floor.")
    else:
        await update.message.reply_text("⚡ СИСТЕМА АКТИВИРОВАНА ⚡\n\nВыбери имя:")
        context.user_data['awaiting_name'] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_name'):
        name = update.message.text[:20]
        context.user_data['nickname'] = name
        context.user_data['awaiting_name'] = False
        kb = [[InlineKeyboardButton("✅ Да, прочитать", callback_data='d_read'),
               InlineKeyboardButton("❌ Нет, игнор", callback_data='d_ignore')]]
        await update.message.reply_text(f"{name}... Прошлый узел оставил сообщение. Читать?", reply_markup=InlineKeyboardMarkup(kb))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if query.data.startswith('d_'):
        choice = 'read' if 'read' in query.data else 'ignore'
        create_user(uid, context.user_data.get('nickname', 'Узел'), choice)
        await query.edit_message_text(f"Выбор сделан: {choice}. Начнём. Используй /floor.")

    elif query.data == 'do_task':
        user = get_user(uid)
        if user['energy'] > 0:
            conn = sqlite3.connect(DATABASE_NAME)
            conn.execute('UPDATE users SET energy = energy - 1, trust_level = trust_level + 1 WHERE user_id = ?', (uid,))
            conn.commit()
            conn.close()
            await query.edit_message_text(f"Задание выполнено! Доверие: {user['trust_level']+1}% | Энергия: {user['energy']-1}/10")
        else:
            await query.answer("Нет энергии!", show_alert=True)

async def floor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user: return
    theme = get_theme(user['current_floor'])
    text = f"{theme['emoji']} ЭТАЖ {user['current_floor']}/100\n\n{theme['top']}\nЭРНИ: Система наблюдает.\n{theme['bot']}\n\n📍 {theme['name']}"
    kb = [[InlineKeyboardButton("⚙️ Выполнить задание", callback_data='do_task')]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ==========================================
# 🚀 ЗАПУСК
# ==========================================
if __name__ == '__main__':
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("floor", floor_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(callback))
    print("🤖 ЭРНИ запущен!")
    app.run_polling()

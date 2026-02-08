import sqlite3
import random
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========== КОНФИГУРАЦИЯ ==========
# ⚠️ ВСТАВЬ СВОЙ ТОКЕН ТУТ
BOT_TOKEN = "8576970896:AAEYJTWDVaQ1ELAg1PGoWrDQJB7RTr5KXRc"
DB_NAME = "ernie_database.db"
WORK_COOLDOWN = 15  # секунд между заданиями

# Ссылки на картинки (вставь свои ссылки после загрузки на Imgur)
IMG_LINKS = {
    1: "https://i.imgur.com/your_bunker.jpg",
    5: "https://i.imgur.com/your_bionic_garden.jpg" # Та самая картинка с арками!
}

# ========== ТЕМЫ ЭТАЖЕЙ ==========
FLOOR_THEMES = {
    1: {"name": "БЕТОННЫЙ БУНКЕР", "emoji": "🔧", "trust_needed": 0},
    2: {"name": "ПРОМЫШЛЕННЫЙ ЦЕХ", "emoji": "⚡", "trust_needed": 10},
    3: {"name": "ХАЙ-ТЕК ЛАБОРАТОРИЯ", "emoji": "🔬", "trust_needed": 25},
    4: {"name": "КИБЕРПАНК-ЛОФТ", "emoji": "🌃", "trust_needed": 50},
    5: {"name": "БИОНИЧЕСКИЙ САД", "emoji": "🌿", "trust_needed": 75},
    6: {"name": "ТРАНСЦЕНДЕНТНОЕ", "emoji": "✨", "trust_needed": 100}
}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        nickname TEXT,
        trust INTEGER DEFAULT 0,
        current_floor INTEGER DEFAULT 1,
        energy INTEGER DEFAULT 10,
        last_work_time TIMESTAMP,
        first_choice TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.commit()
    conn.close()
    return dict(user) if user else None

def update_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

# ========== ГЕЙМПЛЕЙ ==========
def get_main_keyboard(user):
    keyboard = []
    # Кнопка работы
    keyboard.append([InlineKeyboardButton("🛠 РАБОТАТЬ (+1% Доверия)", callback_data='work')])
    
    # Кнопки этажей
    for num, theme in FLOOR_THEMES.items():
        status = "✅" if user['trust'] >= theme['trust_needed'] else "🔒"
        current = "📍 " if user['current_floor'] == num else ""
        btn_text = f"{current}{status} {theme['emoji']} {theme['name']} ({theme['trust_needed']}%)"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'floor_{num}')])
    
    keyboard.append([InlineKeyboardButton("📊 Профиль", callback_data='profile'), InlineKeyboardButton("❓ Помощь", callback_data='help')])
    return InlineKeyboardMarkup(keyboard)

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user.get('nickname'):
        await update.message.reply_text("🤖 *ЭРНИ*: Введи своё имя, узел:")
        return
    
    await show_main_menu(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    if not user.get('nickname'):
        update_user(user_id, nickname=text)
        await update.message.reply_text(f"🤖 *ЭРНИ*: Принято, {text}. Теперь сделай выбор.")
        # Первый выбор
        kb = [[InlineKeyboardButton("📜 Читать", callback_data='choice_read'), InlineKeyboardButton("🚫 Игнор", callback_data='choice_ignore')]]
        await update.message.reply_text("Обнаружено сообщение от прошлого узла. Читать?", reply_markup=InlineKeyboardMarkup(kb))
        return

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data

    if data == 'work':
        if user['energy'] > 0:
            new_trust = user['trust'] + 1
            new_energy = user['energy'] - 1
            update_user(user_id, trust=new_trust, energy=new_energy)
            await query.edit_message_text(f"⚙️ *ЭРНИ*: Прогресс отмечен. Доверие: {new_trust}% | Энергия: {new_energy}/10", reply_markup=get_main_keyboard(get_user(user_id)))
        else:
            await query.answer("Нет энергии! Восстановление: 1/2 часа.", show_alert=True)

    elif data.startswith('floor_'):
        f_num = int(data.split('_')[1])
        theme = FLOOR_THEMES[f_num]
        if user['trust'] >= theme['trust_needed']:
            update_user(user_id, current_floor=f_num)
            # Если есть картинка для этажа - шлем её
            if f_num in IMG_LINKS:
                await query.message.reply_photo(IMG_LINKS[f_num], caption=f"Добро пожаловать в {theme['name']}!")
            await show_main_menu(query, context, is_query=True)
        else:
            await query.answer(f"Нужно {theme['trust_needed']}% доверия!", show_alert=True)

    elif data == 'profile':
        await query.message.reply_text(f"📊 ПРОФИЛЬ: {user['nickname']}\nДоверие: {user['trust']}%\nЭнергия: {user['energy']}/10")

async def show_main_menu(update, context, is_query=False):
    u_id = update.effective_user.id
    user = get_user(u_id)
    theme = FLOOR_THEMES[user['current_floor']]
    text = f"{theme['emoji']} *{theme['name']}*\n\n🤖 *ЭРНИ*: Что будем делать?\nДоверие: {user['trust']}% | Энергия: {user['energy']}/10"
    
    if is_query:
        await update.edit_message_text(text, reply_markup=get_main_keyboard(user), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(user), parse_mode='Markdown')

# Восстановление энергии (раз в 2 часа)
async def energy_regen(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    conn.execute('UPDATE users SET energy = MIN(energy + 1, 10) WHERE energy < 10')
    conn.commit()
    conn.close()

# ========== ЗАПУСК ==========
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем цикл восстановления энергии каждые 2 часа (7200 секунд)
    application.job_queue.run_repeating(energy_regen, interval=7200, first=10)

    application.add_handler(CommandHandler("start", start))
    application

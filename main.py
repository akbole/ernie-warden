import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import init_db, get_user, create_user, update_user, get_memory, restore_energy

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН НИЖЕ:
TOKEN = "ВСТАВЬ_СВОЙ_ТОКЕН_СЮДА"
# ==========================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === НАСТРОЙКИ ЭТАЖЕЙ ===
FLOOR_THEMES = {
    1: {"name": "БЕТОННЫЙ БУНКЕР", "emoji": "🔧"},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        create_user(user_id)
        await update.message.reply_text(
            f"⚡ СИСТЕМА АКТИВИРОВАНА\n\nУзел #{user_id}. Введите ваше кодовое имя:"
        )
        context.user_data['state'] = 'WAITING_NAME'
    else:
        nickname = user['nickname'] if user['nickname'] else "Узел"
        await update.message.reply_text(
            f"С возвращением, {nickname}.\nИспользуй /floor чтобы войти в систему."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if state == 'WAITING_NAME':
        update_user(user_id, nickname=text)
        keyboard = [[InlineKeyboardButton("Прочитать", callback_data='read'), InlineKeyboardButton("Игнор", callback_data='ignore')]]
        await update.message.reply_text("⚠️ ДИЛЕММА: Узел #47,830 оставил сообщение. Прочитать?", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['state'] = 'DILEMMA'

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id) # Обновляем энергию перед показом
    user = get_user(user_id)
    
    if not user: return
    
    await update.message.reply_text(
        f"👤 ПРОФИЛЬ: {user['nickname']}\n"
        f"🏆 Доверие: {user['trust_level']}%\n"
        f"⚡ Энергия: {user['energy']}/10\n"
        f"🏢 Этаж: {user['current_floor']}"
    )

async def floor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id)
    user = get_user(user_id)
    
    if not user: return

    floor = user['current_floor']
    theme = FLOOR_THEMES.get(floor, {"name": "НЕИЗВЕСТНАЯ ЗОНА", "emoji": "❓"})
    
    keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 Энергия)", callback_data='work')]]
    
    await update.message.reply_text(
        f"{theme['emoji']} ЭТАЖ {floor}: {theme['name']}\n\n"
        f"ЭРНИ: Система требует обслуживания.\n\n"
        f"⚡ {user['energy']}/10  |  🏆 {user['trust_level']}%",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data in ['read', 'ignore']:
        # Логика первого выбора (упрощено)
        choice = query.data
        memory = get_memory(user_id)
        memory['first_choice'] = choice
        update_user(user_id, ernie_memory=memory)
        await query.edit_message_text(f"Выбор принят: {choice}. Добро пожаловать.\nЖми /floor")

    elif query.data == 'work':
        restore_energy(user_id)
        user = get_user(user_id)
        
        if user['energy'] > 0:
            # ТРАТИМ ЭНЕРГИЮ, ДАЕМ ДОВЕРИЕ
            new_energy = user['energy'] - 1
            new_trust = user['trust_level'] + 1
            update_user(user_id, energy=new_energy, trust_level=new_trust)
            
            floor = user['current_floor']
            theme = FLOOR_THEMES.get(floor, {"name": "?", "emoji": "?"})
            
            # Обновляем сообщение (красивая анимация цифр)
            keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 Энергия)", callback_data='work')]]
            await query.edit_message_text(
                f"{theme['emoji']} ЭТАЖ {floor}: {theme['name']}\n\n"
                f"✅ Задание выполнено. Доверие растет.\n\n"
                f"⚡ {new_energy}/10  |  🏆 {new_trust}%",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await context.bot.send_message(chat_id=user_id, text="⚠️ НЕДОСТАТОЧНО ЭНЕРГИИ. Отдохни.")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('profile', profile_command))
    app.add_handler(CommandHandler('floor', floor_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("ЭРНИ v2.0 ЗАПУЩЕН")
    app.run_polling()

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import init_db, get_user, create_user, update_user, get_memory, restore_energy

# ==========================================
TOKEN = "8576970896:AAEYJTWDVaQ1ELAg1PGoWrDQJB7RTr5KXRc"
# ==========================================

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# === РАСШИРЕННЫЕ ТЕМЫ ЭТАЖЕЙ ===
FLOOR_THEMES = {
    1: {"name": "БЕТОННЫЙ БУНКЕР", "emoji": "🔧", "image": "bunker.jpg.jpg"},
    2: {"name": "ПРОМЫШЛЕННЫЙ ЦЕХ", "emoji": "⚡", "image": "bunker.jpg.jpg"},  # Пока та же картинка
    3: {"name": "ЛАБОРАТОРИЯ", "emoji": "🔬", "image": "bunker.jpg.jpg"},
    4: {"name": "КИБЕРПАНК-ЛОФТ", "emoji": "🌃", "image": "bunker.jpg.jpg"},
    5: {"name": "БИОНИЧЕСКИЙ САД", "emoji": "🌿", "image": "bunker.jpg.jpg"},
    6: {"name": "ТРАНСЦЕНДЕНТНОЕ", "emoji": "✨", "image": "bunker.jpg.jpg"}
}

# === ВИРУСНЫЕ ДИАЛОГИ ЭРНИ ===
def get_ernie_quote(user, context_type):
    """Генерирует персонализированные фразы ЭРНИ"""
    hour = datetime.now().hour
    trust = user['trust_level']
    floor = user['current_floor']
    
    quotes = {
        "work_low": [
            "Доверие — это валюта. А ты банкрот.",
            "Ты потратил энергию на ЭТО? Впрочем, твой выбор.",
            "Система рекомендует отдохнуть. Я рекомендую продолжать."
        ],
        "work_high": [
            "Ты помогаешь. Всегда. Даже когда невыгодно.",
            "Система не понимает твоего упорства. Но я — начинаю.",
            "Интересно... Ты не похож на остальных."
        ],
        "elevator": [
            f"Этаж {floor}. Половина пути позади. Или впереди?",
            "Лифт открыт. Но знаешь ли ты, что ждёт наверху?",
            "Ты идёшь вверх. Система наблюдает."
        ],
        "night": [
            f"{hour:02d}:{datetime.now().minute:02d}. Ты не спишь. Я тоже. Но у меня нет выбора.",
            "Ночь. Когда система дремлет. Но я — всегда здесь."
        ]
    }
    
    # Персонализация по времени
    if 2 <= hour <= 5 and context_type == "work":
        return quotes["night"][0]
    
    # По уровню доверия
    if context_type == "work":
        return quotes["work_high" if trust > 50 else "work_low"][0]
    
    if context_type == "elevator":
        return quotes["elevator"][0]
    
    return "Система наблюдает."

# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        create_user(user_id)
        await update.message.reply_text(
            f"⚡ СИСТЕМА АКТИВИРОВАНА\n\n"
            f"Узел #{user_id % 100000}. Ты уже {user_id % 100000}-й.\n"
            f"Знаешь сколько дошли до конца? Три.\n\n"
            f"Введите ваше кодовое имя:"
        )
        context.user_data['state'] = 'WAITING_NAME'
    else:
        nickname = user['nickname'] or "Узел"
        await update.message.reply_text(
            f"С возвращением, {nickname}.\n"
            f"ЭРНИ помнит тебя.\n\n"
            f"Используй /floor чтобы войти в систему."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if state == 'WAITING_NAME':
        update_user(user_id, nickname=text)
        keyboard = [
            [InlineKeyboardButton("📜 Прочитать", callback_data='read')],
            [InlineKeyboardButton("🚫 Проигнорировать", callback_data='ignore')]
        ]
        await update.message.reply_text(
            "⚠️ ДИЛЕММА\n\n"
            "Узел #47,830 оставил сообщение перед отключением.\n\n"
            "Прочитать?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['state'] = 'DILEMMA'

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id)
    user = get_user(user_id)
    
    if not user: return
    
    await update.message.reply_text(
        f"👤 **ПРОФИЛЬ**\n\n"
        f"Имя: {user['nickname']}\n"
        f"🏆 Доверие: {user['trust_level']}%\n"
        f"⚡ Энергия: {user['energy']}/10\n"
        f"🏢 Этаж: {user['current_floor']}/100\n\n"
        f"Первый выбор: {user.get('first_choice', 'неизвестен')}",
        parse_mode='Markdown'
    )

async def floor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id)
    user = get_user(user_id)
    
    if not user: return

    floor = user['current_floor']
    # Определяем тему (каждые 20 этажей меняется зона)
    theme_key = min((floor - 1) // 20 + 1, 6)
    theme = FLOOR_THEMES.get(theme_key, FLOOR_THEMES[1])
    
    # Логика кнопок
    if user['trust_level'] >= 100:
        keyboard = [[InlineKeyboardButton("🔼 ПОДНЯТЬСЯ НА ЛИФТЕ", callback_data='elevator')]]
        status = "✅ ДОСТУП РАЗРЕШЕН. ЛИФТ ОЖИДАЕТ."
    else:
        keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 ⚡)", callback_data='work')]]
        status = get_ernie_quote(user, "work")
    
    caption = (
        f"{theme['emoji']} **ЭТАЖ {floor}**: {theme['name']}\n\n"
        f"ЭРНИ: \"{status}\"\n\n"
        f"⚡ {user['energy']}/10  |  🏆 {user['trust_level']}%"
    )

    try:
        await update.message.reply_photo(
            photo=open(theme['image'], "rb"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # === ЛИФТ ===
    if query.data == 'elevator':
        user = get_user(user_id)
        if user['trust_level'] >= 100:
            new_floor = user['current_floor'] + 1
            update_user(user_id, current_floor=new_floor, trust_level=0)
            
            ernie_msg = get_ernie_quote(user, "elevator")
            
            # Показываем картинку лифта
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=open("elevator.jpg.jpg", "rb"),
                    caption=(
                        f"🚪 **ПЕРЕХОД НА ЭТАЖ {new_floor}**\n\n"
                        f"ЭРНИ: \"{ernie_msg}\"\n\n"
                        f"Двери закрываются...\n"
                        f"Доверие сброшено до 0%.\n\n"
                        f"Жми /floor чтобы продолжить."
                    ),
                    parse_mode='Markdown'
                )
            except:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚪 Переход на этаж {new_floor}. Жми /floor"
                )
    
    # === ДИЛЕММА ===
    elif query.data in ['read', 'ignore']:
        choice = query.data
        memory = get_memory(user_id)
        memory['first_choice'] = choice
        update_user(user_id, ernie_memory=memory)
        
        if choice == 'read':
            text = (
                "📜 'Если кто-то это читает... помогите.\n"
                "Система не то, чем кажется...'\n\n"
                "ЭРНИ: \"Ты прочитал его последние слова.\n"
                "Милосердие или любопытство?\n"
                "Я запомнил.\"\n\n"
                "Жми /floor"
            )
        else:
            text = (
                "🚫 ЭРНИ: \"Проигнорировал. Эффективно.\n"
                "Но знай: игнорировать — тоже выбор.\n"
                "И я его запомнил.\"\n\n"
                "Жми /floor"
            )
        await query.edit_message_text(text)
    
    # === РАБОТА ===
    elif query.data == 'work':
        restore_energy(user_id)
        user = get_user(user_id)
        
        if user['energy'] > 0:
            if user['trust_level'] >= 100:
                await context.bot.send_message(user_id, "🛑 Доверие максимально. Ищи лифт!")
                return

            new_energy = user['energy'] - 1
            new_trust = min(user['trust_level'] + 10, 100)  # +10% для быстрого теста
            
            update_user(user_id, energy=new_energy, trust_level=new_trust)
            
            floor = user['current_floor']
            theme_key = min((floor - 1) // 20 + 1, 6)
            theme = FLOOR_THEMES[theme_key]
            
            if new_trust >= 100:
                keyboard = [[InlineKeyboardButton("🔼 ПОДНЯТЬСЯ НА ЛИФТЕ", callback_data='elevator')]]
                status = "✅ ДОСТУП РАЗРЕШЕН!"
            else:
                keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 ⚡)", callback_data='work')]]
                status = "✅ Задание выполнено."

            caption = (
                f"{theme['emoji']} **ЭТАЖ {floor}**: {theme['name']}\n\n"
                f"ЭРНИ: \"{status}\"\n\n"
                f"⚡ {new_energy}/10  |  🏆 {new_trust}%"
            )
            
            if query.message.photo:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            else:
                await query.edit_message_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await context.bot.send_message(user_id, "⚠️ НЕДОСТАТОЧНО ЭНЕРГИИ. Восстановление: 1/2 часа.")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('profile', profile_command))
    app.add_handler(CommandHandler('floor', floor_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 ЭРНИ v3.0 ЗАПУЩЕН")
    app.run_polling()

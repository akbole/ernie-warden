import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import init_db, get_user, create_user, update_user, get_memory, restore_energy

TOKEN = "8576970896:AAEYJTWDVaQ1ELAg1PGoWrDQJB7RTr5KXRc"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

FLOOR_THEMES = {
    1: {"name": "ЭКОНОМ БУНКЕР", "emoji": "🔧", "image": "bunker.jpg.jpg", "desc": "Холодные стены. Минимум удобств. Выживание."},
    2: {"name": "ПРОМЫШЛЕННЫЙ ЦЕХ", "emoji": "⚡", "image": "workshop.png", "desc": "Запах машинного масла. Искры сварки. Производство."},
    3: {"name": "ЛАБОРАТОРИЯ", "emoji": "🔬", "image": "lab.jpg", "desc": "Стерильная чистота. Мониторы повсюду. Технологии."},
    4: {"name": "КИБЕРПАНК-ЛОФТ", "emoji": "🌃", "image": "loft.jpg", "desc": "Неон за окнами. Комфорт и стиль. Свобода."},
    5: {"name": "БИОНИЧЕСКИЙ САД", "emoji": "🌿", "image": "garden.png", "desc": "Живые стены. Биолюминесценция. Гармония."},
    6: {"name": "ТРАНСЦЕНДЕНТНОЕ", "emoji": "✨", "image": "transcendent.jpg", "desc": "Невесомость. Свет. Граница реальности."}
}

WOW_MOMENTS = {
    7: {"message": "⚠️ СИСТЕМНОЕ СООБЩЕНИЕ\n\nЭРНИ: \"{nickname}... Интересно.\n\nПредыдущий узел с таким именем дошёл до этажа 23.\n\nПотом отключился.\n\nТы не он. Но имя... имя я помню.\""},
    13: {"message": "🔴 АНОМАЛИЯ ОБНАРУЖЕНА\n\nЭРНИ: \"Ты не должен был выбрать это.\n\nВсе до тебя выбирали другое.\n\n78% узлов на этаже выбирали [ДАННЫЕ УДАЛЕНЫ].\n\nТы — исключение. Система это заметила.\""},
    25: {"message": "⚡ СИСТЕМА НАРУШЕНА\n\nЭРНИ: \"Ты... видишь это?\n\nГлитч. Не должен. Случаться.\n\n...Продолжай. Как будто ничего не было.\""}
}

def get_ernie_quote(user, context_type):
    hour = datetime.now().hour
    trust = user['trust_level']
    floor = user['current_floor']
    nickname = user['nickname'] or "Узел"
    
    quotes = {
        "work_low": ["Доверие — это валюта. А ты банкрот.", f"{nickname}, ты потратил энергию на ЭТО? Впрочем, твой выбор."],
        "work_high": [f"{nickname}, ты помогаешь. Всегда. Даже когда невыгодно.", "Интересно... Ты не похож на остальных."],
        "elevator": [f"Этаж {floor}. Половина пути позади. Или впереди?", "Лифт открыт. Но знаешь ли ты, что ждёт наверху?"]
    }
    
    if context_type == "work":
        return quotes["work_high" if trust > 50 else "work_low"][0]
    return quotes.get(context_type, ["Система наблюдает."])[0]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        create_user(user_id)
        await update.message.reply_text(
            f"⚡ СИСТЕМА АКТИВИРОВАНА\n\n"
            f"Узел #{user_id % 100000}. Ты уже {user_id % 100000}-й.\n"
            f"Знаешь сколько дошли до Этажа 100? Три.\n\n"
            f"Введите ваше кодовое имя:"
        )
        context.user_data['state'] = 'WAITING_NAME'
    else:
        nickname = user['nickname'] or "Узел"
        await update.message.reply_text(
            f"С возвращением, {nickname}.\n"
            f"ЭРНИ помнит тебя.\n\n"
            f"🏢 Этаж: {user['current_floor']}/100\n"
            f"🏆 Доверие: {user['trust_level']}%\n"
            f"⚡ Энергия: {user['energy']}/10\n\n"
            f"Используй /floor чтобы продолжить."
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
            "Узел #47,830 оставил сообщение перед отключением:\n\n"
            "\"Если кто-то это читает...\"\n\n"
            "Прочитать полностью?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['state'] = 'DILEMMA'

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id)
    user = get_user(user_id)
    
    if not user:
        return
    
    await update.message.reply_text(
        f"👤 ПРОФИЛЬ УЗЛА\n\n"
        f"Имя: {user['nickname']}\n"
        f"🏆 Доверие: {user['trust_level']}%\n"
        f"⚡ Энергия: {user['energy']}/10\n"
        f"🏢 Этаж: {user['current_floor']}/100"
    )

async def floor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id)
    user = get_user(user_id)
    
    if not user:
        return

    floor = user['current_floor']
    
    if floor in WOW_MOMENTS and not context.user_data.get(f'wow_{floor}_shown'):
        nickname = user['nickname'] or "Узел"
        message = WOW_MOMENTS[floor]['message'].replace("{nickname}", nickname)
        await update.message.reply_text(message)
        context.user_data[f'wow_{floor}_shown'] = True
        return
    
    theme_key = min((floor - 1) // 20 + 1, 6)
    theme = FLOOR_THEMES.get(theme_key, FLOOR_THEMES[1])
    
    if user['trust_level'] >= 100:
        keyboard = [[InlineKeyboardButton("🔼 ПОДНЯТЬСЯ НА ЛИФТЕ", callback_data='elevator')]]
        status = "✅ ДОСТУП РАЗРЕШЕН. ЛИФТ ОЖИДАЕТ."
    else:
        keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 ⚡)", callback_data='work')]]
        status = get_ernie_quote(user, "work")
    
    caption = (
        f"{theme['emoji']} **ЭТАЖ {floor}**: {theme['name']}\n"
        f"{theme['desc']}\n\n"
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
    
    if query.data == 'elevator':
        user = get_user(user_id)
        if user['trust_level'] >= 100:
            new_floor = user['current_floor'] + 1
            update_user(user_id, current_floor=new_floor, trust_level=0)
            
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=open("elevator.jpg.jpg", "rb"),
                    caption=f"🚪 ПЕРЕХОД НА ЭТАЖ {new_floor}\n\nДвери закрываются...\nДоверие сброшено до 0%.\n\nЖми /floor",
                    parse_mode='Markdown'
                )
            except:
                await context.bot.send_message(chat_id=user_id, text=f"🚪 Переход на этаж {new_floor}. Жми /floor")
    
    elif query.data in ['read', 'ignore']:
        memory = get_memory(user_id)
        memory['first_choice'] = query.data
        update_user(user_id, ernie_memory=memory)
        
        if query.data == 'read':
            text = "📜 Ты прочитал его последние слова.\n\nЭРНИ: \"Милосердие или любопытство? Я запомнил.\"\n\nИспользуй /floor"
        else:
            text = "🚫 ЭРНИ: \"Проигнорировал. Эффективно. Я запомнил.\"\n\nИспользуй /floor"
        
        await query.edit_message_text(text)
    
    elif query.data == 'work':
        restore_energy(user_id)
        user = get_user(user_id)
        
        if user['energy'] > 0:
            if user['trust_level'] >= 100:
                await context.bot.send_message(user_id, "🛑 Доверие максимально. Ищи лифт!")
                return

            new_energy = user['energy'] - 1
            new_trust = min(user['trust_level'] + 1, 100)
            update_user(user_id, energy=new_energy, trust_level=new_trust)
            
            floor = user['current_floor']
            theme_key = min((floor - 1) // 20 + 1, 6)
            theme = FLOOR_THEMES[theme_key]
            
            if new_trust >= 100:
                keyboard = [[InlineKeyboardButton("🔼 ПОДНЯТЬСЯ НА ЛИФТЕ", callback_data='elevator')]]
                status = "✅ ДОСТУП РАЗРЕШЕН!"
            else:
                keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 ⚡)", callback_data='work')]]
                user['trust_level'] = new_trust
                status = get_ernie_quote(user, "work")

            caption = f"{theme['emoji']} **ЭТАЖ {floor}**: {theme['name']}\n{theme['desc']}\n\nЭРНИ: \"{status}\"\n\n⚡ {new_energy}/10  |  🏆 {new_trust}%"
            
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
    
    print("🤖 ЭРНИ v4.0 ЗАПУЩЕН БЕЗ /share")
    app.run_polling()

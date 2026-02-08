import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import init_db, get_user, create_user, update_user, get_memory

# ==========================================
# ВСТАВЬ СЮДА СВОЙ ТОКЕН ВНУТРИ КАВЫЧЕК:
TOKEN = "8576970896:AAEYJTWDVaQ1ELAg1PGoWrDQJB7RTr5KXRc"
# ==========================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        create_user(user_id)
        # ЭМОЦИОНАЛЬНЫЙ ХАЙДЖЕК (Первый контакт)
        await update.message.reply_text(
            f"⚡ СИСТЕМА АКТИВИРОВАНА\n\n"
            f"Узел #{user_id}. Ты уже {user_id}-й.\n"
            "Знаешь сколько дошли до конца? Три.\n"
            "Будешь четвёртым или забудешься через неделю?\n\n"
            "Введите ваше кодовое имя:"
        )
        context.user_data['state'] = 'WAITING_NAME'
    else:
        nickname = user['nickname'] if user['nickname'] else "Узел"
        await update.message.reply_text(f"С возвращением, {nickname}. ЭРНИ помнит тебя.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if state == 'WAITING_NAME':
        nickname = text
        update_user(user_id, nickname=nickname)
        
        # ВАУ-МОМЕНТ: Реакция на имя
        await update.message.reply_text(
            f"{nickname}... Интересно.\n"
            f"Предыдущий узел с таким именем дошёл до этажа 23.\n"
            f"Совпадение? Не думаю."
        )
        
        # МОРАЛЬНАЯ ДИЛЕММА
        keyboard = [
            [InlineKeyboardButton("Прочитать сообщение", callback_data='read')],
            [InlineKeyboardButton("Проигнорировать", callback_data='ignore')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ ВНИМАНИЕ: ОБНАРУЖЕН ФАЙЛ\n\n"
            "Узел #47,830 оставил сообщение перед отключением.\n"
            "Прочитать?",
            reply_markup=reply_markup
        )
        context.user_data['state'] = 'DILEMMA'

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'read':
        memory = get_memory(user_id)
        memory['first_choice'] = 'read'
        update_user(user_id, ernie_memory=memory)

        await query.edit_message_text(
            "📜 'Если кто-то это читает... помогите. Система не то, чем кажется...'\n\n"
            "Ты прочитал его последние слова.\n"
            "Милосердие или любопытство? Не важно.\n"
            "Теперь его история — твоя ноша."
        )
    
    elif query.data == 'ignore':
        memory = get_memory(user_id)
        memory['first_choice'] = 'ignore'
        update_user(user_id, ernie_memory=memory)

        await query.edit_message_text(
            "🚫 Проигнорировал. Эффективно.\n"
            "Но знай: игнорировать — тоже выбор.\n"
            "И я его запомнил."
        )

    await context.bot.send_message(chat_id=user_id, text="Добро пожаловать на Этаж 1.\nНачнем.")
    context.user_data['state'] = 'GAME_LOOP'

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("ЭРНИ ЗАПУЩЕН. СИСТЕМА ОНЛАЙН.")
    app.run_polling()

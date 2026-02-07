import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
user_trust = 5 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_trust
    user_trust = 5 
    keyboard = [[InlineKeyboardButton("👀 Осмотреться", callback_data="look")]]
    await update.message.reply_text(
        "Соединение установлено.\n\nТы в Лобби.\n\n"
        f"Доверие: {user_trust}%\n\nЧто будешь делать?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_trust
    query = update.callback_query
    await query.answer()
    if query.data == "look":
        keyboard = [[InlineKeyboardButton("🚪 Лифт", callback_data="elevator")]]
        await query.edit_message_text("Бетонные стены. Система шепчет: «Не трать ресурсы».", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "elevator":
        keyboard = [[InlineKeyboardButton("🛠 Работать", callback_data="work")]]
        await query.edit_message_text(f"🚫 ДОСТУП ЗАПРЕЩЕН\nНужно 50%\nУ тебя: {user_trust}%", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "work":
        user_trust += 1
        text = f"✅ Доверие +1% ({user_trust}%)\nЭрни: «Терпение — навык»." if user_trust < 50 else "🎉 ЛИФТ ОТКРЫТ!"
        await query.edit_message_text(text)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

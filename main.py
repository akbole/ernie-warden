import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

TOKEN = "8576970896:AAEYJTWDVaQ1ELAg1PGoWrDQJB7RTr5KXRc"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    await update.message.reply_text(
        f"✅ БОТ РАБОТАЕТ!\n\n"
        f"👤 ID: {user_id}\n"
        f"📝 Username: @{username}\n\n"
        f"Это тестовая версия для проверки связи."
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    
    print("🤖 ТЕСТОВЫЙ БОТ ЗАПУЩЕН - БЕЗ БАЗЫ ДАННЫХ")
    app.run_polling()

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import init_db, get_user, create_user, update_user, get_memory, restore_energy
import io
from PIL import Image, ImageDraw, ImageFont

# ==========================================
TOKEN = "8576970896:AAEYJTWDVaQ1ELAg1PGoWrDQJB7RTr5KXRc"
# ==========================================

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# === РАСШИРЕННЫЕ ТЕМЫ ЭТАЖЕЙ ===
FLOOR_THEMES = {
    1: {"name": "ЭКОНОМ БУНКЕР", "emoji": "🔧", "image": "bunker.jpg.jpg", "desc": "Холодные стены. Минимум удобств. Выживание."},
    2: {"name": "ПРОМЫШЛЕННЫЙ ЦЕХ", "emoji": "⚡", "image": "workshop.jpg", "desc": "Запах машинного масла. Искры сварки. Производство."},
    3: {"name": "ЛАБОРАТОРИЯ", "emoji": "🔬", "image": "lab.jpg", "desc": "Стерильная чистота. Мониторы повсюду. Технологии."},
    4: {"name": "КИБЕРПАНК-ЛОФТ", "emoji": "🌃", "image": "loft.jpg", "desc": "Неон за окнами. Комфорт и стиль. Свобода."},
    5: {"name": "БИОНИЧЕСКИЙ САД", "emoji": "🌿", "image": "garden.jpg", "desc": "Живые стены. Биолюминесценция. Гармония."},
    6: {"name": "ТРАНСЦЕНДЕНТНОЕ", "emoji": "✨", "image": "transcendent.jpg", "desc": "Невесомость. Свет. Граница реальности."}
}

# === ВАУ-МОМЕНТЫ ===
WOW_MOMENTS = {
    7: {
        "trigger": True,
        "message": "⚠️ СИСТЕМНОЕ СООБЩЕНИЕ\n\nЭРНИ: \"{nickname}... Интересно.\n\nПредыдущий узел с таким именем дошёл до этажа 23.\n\nПотом отключился.\n\nТы не он. Но имя... имя я помню.\""
    },
    13: {
        "trigger": True,
        "message": "🔴 АНОМАЛИЯ ОБНАРУЖЕНА\n\nЭРНИ: \"Ты не должен был выбрать это.\n\nВсе до тебя выбирали другое.\n\n78% узлов на этаже выбирали [ДАННЫЕ УДАЛЕНЫ].\n\nТы — исключение. Система это заметила.\""
    },
    25: {
        "trigger": True,
        "message": "⚡ С̶И̶С̶Т̶Е̶М̶А̶ ̶Н̶А̶Р̶У̶Ш̶Е̶Н̶А̶\n\nЭ̷Р̷Н̷И̷:̷ ̷\"̷Т̷ы̷.̷.̷.̷ ̷в̷и̷д̷и̷ш̷ь̷ ̷э̷т̷о̷?̷\n\nГ̶л̶и̶т̶ч̶.̶ ̶Н̶е̶ ̶д̶о̶л̶ж̶е̶н̶.̶ ̶С̶л̶у̶ч̶а̶т̶ь̶с̶я̶.̶\n\n...Продолжай. Как будто ничего не было.\""
    }
}

# === ВИРУСНЫЕ ДИАЛОГИ ЭРНИ ===
def get_ernie_quote(user, context_type):
    """Генерирует персонализированные фразы ЭРНИ"""
    hour = datetime.now().hour
    trust = user['trust_level']
    floor = user['current_floor']
    nickname = user['nickname'] or "Узел"
    
    quotes = {
        "work_low": [
            "Доверие — это валюта. А ты банкрот.",
            f"{nickname}, ты потратил энергию на ЭТО? Впрочем, твой выбор.",
            "Система рекомендует отдохнуть. Я рекомендую продолжать.",
            "Эффективность: 12%. Но ты стараешься."
        ],
        "work_medium": [
            f"{nickname}... Ты не сдаёшься. Интересно.",
            "47% пути. Большинство сдались на 30%.",
            "Система не понимает твоего упорства.",
            "Продолжай. Я наблюдаю."
        ],
        "work_high": [
            f"{nickname}, ты помогаешь. Всегда. Даже когда невыгодно.",
            "Система не понимает твоего упорства. Но я — начинаю.",
            "Интересно... Ты не похож на остальных.",
            f"Доверие: {trust}%. Ты близко, {nickname}."
        ],
        "elevator_low": [
            f"Этаж {floor}. Большинство не прошли дальше 15.",
            "Лифт открыт. Но знаешь ли ты, что ждёт наверху?",
            "Ты идёшь вверх. Система наблюдает."
        ],
        "elevator_high": [
            f"Этаж {floor}. Половина пути позади. Или впереди?",
            f"{nickname}... Мало кто доходит так далеко.",
            "Ты поднимаешься. Я помню каждый твой выбор."
        ],
        "night": [
            f"{hour:02d}:{datetime.now().minute:02d}. Ты не спишь. Я тоже. Но у меня нет выбора.",
            "Ночь. Когда система дремлет. Но я — всегда здесь.",
            f"{nickname}, ты один не спишь на этом этаже. Сейчас."
        ]
    }
    
    # Персонализация по времени
    if 2 <= hour <= 5 and context_type == "work":
        return quotes["night"][hour % len(quotes["night"])]
    
    # По уровню доверия
    if context_type == "work":
        if trust < 30:
            return quotes["work_low"][floor % len(quotes["work_low"])]
        elif trust < 70:
            return quotes["work_medium"][floor % len(quotes["work_medium"])]
        else:
            return quotes["work_high"][floor % len(quotes["work_high"])]
    
    if context_type == "elevator":
        if floor < 50:
            return quotes["elevator_low"][floor % len(quotes["elevator_low"])]
        else:
            return quotes["elevator_high"][floor % len(quotes["elevator_high"])]
    
    return "Система наблюдает."

# === ФУНКЦИЯ ДЛЯ ГЕНЕРАЦИИ SHARE КАРТОЧКИ ===
def generate_share_card(user):
    """Генерирует вирусную карточку прогресса"""
    
    # Создаём изображение
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Пытаемся загрузить шрифт
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    nickname = user['nickname'] or "Узел"
    floor = user['current_floor']
    trust = user['trust_level']
    
    # Определяем зону
    zone_key = min((floor - 1) // 20 + 1, 6)
    zone = FLOOR_THEMES.get(zone_key, FLOOR_THEMES[1])
    
    # Рисуем контент
    draw.text((400, 80), f"УЗЕЛ: {nickname}", fill='#00d9ff', anchor="mm", font=font_title)
    draw.text((400, 180), f"🏢 ЭТАЖ {floor}/100", fill='#ffffff', anchor="mm", font=font_text)
    draw.text((400, 240), f"{zone['emoji']} {zone['name']}", fill='#16c79a', anchor="mm", font=font_text)
    draw.text((400, 300), f"🏆 ДОВЕРИЕ: {trust}%", fill='#f39c12', anchor="mm", font=font_text)
    
    # Статистика
    draw.text((400, 380), f"Пройдено: {floor}%", fill='#95a5a6', anchor="mm", font=font_small)
    draw.text((400, 420), f"До вершины: {100 - floor} этажей", fill='#95a5a6', anchor="mm", font=font_small)
    
    # Брендинг
    draw.text((400, 520), "ЭРНИ: Telegram RPG", fill='#7f8c8d', anchor="mm", font=font_small)
    draw.text((400, 550), "Создано через Claude.ai", fill='#555555', anchor="mm", font=font_small)
    
    # Сохраняем в BytesIO
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        create_user(user_id)
        await update.message.reply_text(
            f"⚡ СИСТЕМА АКТИВИРОВАНА\n\n"
            f"Узел #{user_id % 100000}. Ты уже {user_id % 100000}-й.\n"
            f"Знаешь сколько дошли до Этажа 100? Три.\n\n"
            f"0.3% доходят до Этажа 10.\n\n"
            f"Введите ваше кодовое имя:"
        )
        context.user_data['state'] = 'WAITING_NAME'
    else:
        nickname = user['nickname'] or "Узел"
        await update.message.reply_text(
            f"С возвращением, {nickname}.\n"
            f"ЭРНИ помнит тебя.\n\n"
            f"📊 Твой прогресс:\n"
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
    
    if not user: return
    
    memory = get_memory(user_id)
    first_choice = memory.get('first_choice', 'неизвестен')
    
    await update.message.reply_text(
        f"👤 **ПРОФИЛЬ УЗЛА**\n\n"
        f"Имя: {user['nickname']}\n"
        f"🏆 Доверие: {user['trust_level']}%\n"
        f"⚡ Энергия: {user['energy']}/10\n"
        f"🏢 Этаж: {user['current_floor']}/100\n\n"
        f"📜 Первый выбор: {first_choice}\n"
        f"📅 Создан: {user['created_at'][:10]}",
        parse_mode='Markdown'
    )

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирует вирусную карточку прогресса"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ Сначала пройди регистрацию: /start")
        return
    
    await update.message.reply_text("🎨 Генерирую твою карточку прогресса...")
    
    try:
        card_image = generate_share_card(user)
        
        nickname = user['nickname'] or "Узел"
        floor = user['current_floor']
        
        caption = (
            f"📊 **ПРОГРЕСС УЗЛА {nickname.upper()}**\n\n"
            f"🏢 Этаж {floor}/100\n"
            f"🏆 Доверие: {user['trust_level']}%\n\n"
            f"Сколько этажей пройдёшь ты?\n\n"
            f"🤖 ЭРНИ — атмосферная RPG в Telegram\n"
            f"✨ Создано через Claude.ai"
        )
        
        await update.message.reply_photo(
            photo=card_image,
            caption=caption,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"⚠️ Ошибка генерации карточки: {e}")
        await update.message.reply_text(
            f"📊 **ПРОГРЕСС {user['nickname'].upper()}**\n\n"
            f"🏢 Этаж: {user['current_floor']}/100\n"
            f"🏆 Доверие: {user['trust_level']}%\n"
            f"⚡ Энергия: {user['energy']}/10\n\n"
            f"Поделись своим прогрессом! 🚀",
            parse_mode='Markdown'
        )

async def floor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    restore_energy(user_id)
    user = get_user(user_id)
    
    if not user: return

    floor = user['current_floor']
    
    # Проверка вау-момента
    if floor in WOW_MOMENTS and not context.user_data.get(f'wow_{floor}_shown'):
        wow = WOW_MOMENTS[floor]
        nickname = user['nickname'] or "Узел"
        message = wow['message'].replace("{nickname}", nickname)
        
        await update.message.reply_text(message)
        context.user_data[f'wow_{floor}_shown'] = True
        return
    
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
        print(f"⚠️ Ошибка загрузки {theme['image']}: {e}")
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
            except Exception as e:
                print(f"⚠️ Ошибка загрузки лифта: {e}")
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
                "📜 **ПОСЛЕДНЕЕ СООБЩЕНИЕ УЗЛА #47,830**\n\n"
                "\"Если кто-то это читает... помогите.\n"
                "Система не то, чем кажется.\n"
                "На этаже 47 я понял—\"\n\n"
                "[СООБЩЕНИЕ ОБРЫВАЕТСЯ]\n\n"
                "ЭРНИ: \"Ты прочитал его последние слова.\n"
                "Милосердие или любопытство?\n"
                "Я запомнил.\"\n\n"
                "Используй /floor чтобы начать."
            )
        else:
            text = (
                "🚫 **СООБЩЕНИЕ ПРОИГНОРИРОВАНО**\n\n"
                "ЭРНИ: \"Проигнорировал. Эффективно.\n\n"
                "Но знай: игнорировать — тоже выбор.\n"
                "И я его запомнил.\n\n"
                "78% узлов выбирают так же.\"\n\n"
                "Используй /floor чтобы начать."
            )
        await query.edit_message_text(text, parse_mode='Markdown')
    
    # === РАБОТА ===
    elif query.data == 'work':
        restore_energy(user_id)
        user = get_user(user_id)
        
        if user['energy'] > 0:
            if user['trust_level'] >= 100:
                await context.bot.send_message(user_id, "🛑 Доверие максимально. Ищи лифт!")
                return

            new_energy = user['energy'] - 1
            new_trust = min(user['trust_level'] + 1, 100)  # ✅ +1% за задание
            
            update_user(user_id, energy=new_energy, trust_level=new_trust)
            
            floor = user['current_floor']
            theme_key = min((floor - 1) // 20 + 1, 6)
            theme = FLOOR_THEMES[theme_key]
            
            if new_trust >= 100:
                keyboard = [[InlineKeyboardButton("🔼 ПОДНЯТЬСЯ НА ЛИФТЕ", callback_data='elevator')]]
                status = "✅ ДОСТУП РАЗРЕШЕН!"
            else:
                keyboard = [[InlineKeyboardButton("🛠 Выполнить задание (-1 ⚡)", callback_data='work')]]
                # Обновляем пользователя для правильной цитаты
                user['trust_level'] = new_trust
                user['energy'] = new_energy
                status = get_ernie_quote(user, "work")

            caption = (
                f"{theme['emoji']} **ЭТАЖ {floor}**: {theme['name']}\n"
                f"{theme['desc']}\n\n"
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
    app.add_handler(CommandHandler('share', share_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 ЭРНИ v4.0 ЗАПУЩЕН | Доверие: +1% | Зоны: 6 | Вау: 3 | Share: ✅")
    app.run_polling()
```

---

## 3️⃣ **Загрузи на GitHub все файлы:**

После конвертации должно быть:
```
bunker.jpg.jpg
elevator.jpg.jpg
workshop.jpg
lab.jpg
loft.jpg
garden.jpg
transcendent.jpg
main.py (обновлённый)
database.py
floor_themes.py
requirements.txt
Procfile

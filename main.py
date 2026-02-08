"""
ERNIE - Telegram RPG с живым ИИ-персонажем
Полная версия игры в одном файле
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
# ⚠️ ВАЖНО: ЗАМЕНИ ЭТОТ ТОКЕН НА СВОЙ!
BOT_TOKEN = os.getenv('BOT_TOKEN', '7933434246:AAErOnLbmRoQrVWnwlnq_Wa7pWiYFAYE7P8')
DB_NAME = "ernie_database.db"
WORK_COOLDOWN = 30  # секунд между заданиями

# ========== ТЕМЫ ЭТАЖЕЙ ==========
FLOOR_THEMES = {
    1: {"name": "БЕТОННЫЙ БУНКЕР", "emoji": "🔧", "color": "gray", "trust_needed": 0},
    2: {"name": "ПРОМЫШЛЕННЫЙ ЦЕХ", "emoji": "⚡", "color": "blue", "trust_needed": 10},
    3: {"name": "ХАЙ-ТЕК ЛАБОРАТОРИЯ", "emoji": "🔬", "color": "cyan", "trust_needed": 25},
    4: {"name": "КИБЕРПАНК-ЛОФТ", "emoji": "🌃", "color": "purple", "trust_needed": 50},
    5: {"name": "БИОНИЧЕСКИЙ САД", "emoji": "🌿", "color": "green", "trust_needed": 75},
    6: {"name": "ТРАНСЦЕНДЕНТНОЕ ПРОСТРАНСТВО", "emoji": "✨", "color": "gold", "trust_needed": 100}
}

# Сообщения ЭРНИ
ERNIE_MESSAGES = {
    "welcome": [
        "Узел #{user_id}. Ты уже {user_id}-й. Знаешь сколько из вас дошли до конца? Три. Будешь четвёртым или забудешься через неделю?",
        "Ещё один. Номер {user_id}. Статистика показывает, что 0.3% доходят до Этажа 100.",
        "Подключение установлено. Узел #{user_id}. Начнём?"
    ],
    "work": [
        "Доверие зафиксировано. +1%",
        "Прогресс отмечен. Система наблюдает.",
        "Задание выполнено. Ты полезен."
    ],
    "floor_unlocked": [
        "Доступ разрешён. Добро пожаловать.",
        "Ты прошёл проверку. Входи.",
        "Интересно... ты достоин."
    ],
    "floor_locked": [
        "Доступ запрещён. Вернись позже.",
        "Недостаточно доверия. Работай усерднее.",
        "Ты ещё не готов."
    ]
}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    """Инициализация базы данных"""
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
    """Получить данные пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Создаем пользователя если его нет
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, trust, current_floor, energy)
    VALUES (?, 0, 1, 10)
    ''', (user_id,))
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        columns = [desc[0] for desc in cursor.description]
        user_dict = dict(zip(columns, user))
    else:
        user_dict = None
    
    conn.commit()
    conn.close()
    return user_dict

def update_user(user_id, **kwargs):
    """Обновить данные пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(user_id)
    
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

# ========== ГЕЙМПЛЕЙНЫЕ ФУНКЦИИ ==========
def get_floor_theme(floor_number):
    """Получить тему для этажа"""
    if floor_number <= 10:
        return FLOOR_THEMES[1]
    elif floor_number <= 30:
        return FLOOR_THEMES[2]
    elif floor_number <= 50:
        return FLOOR_THEMES[3]
    elif floor_number <= 70:
        return FLOOR_THEMES[4]
    elif floor_number <= 90:
        return FLOOR_THEMES[5]
    else:
        return FLOOR_THEMES[6]

def get_ernie_message(key, user_id=None):
    """Получить случайное сообщение ЭРНИ"""
    messages = ERNIE_MESSAGES.get(key, [])
    if not messages:
        return ""
    
    message = random.choice(messages)
    if user_id and "{user_id}" in message:
        message = message.replace("{user_id}", str(user_id % 100000))
    return message

def get_main_keyboard(user):
    """Создать основную клавиатуру"""
    keyboard = []
    
    # Кнопка работы
    last_work = user.get('last_work_time')
    can_work = True
    
    if last_work:
        try:
            last_time = datetime.fromisoformat(last_work) if isinstance(last_work, str) else datetime.fromtimestamp(last_work)
            if datetime.now() - last_time < timedelta(seconds=WORK_COOLDOWN):
                can_work = False
        except:
            can_work = True
    
    work_text = f"{'⏳' if not can_work else '⚙️'} {'ОЖИДАНИЕ' if not can_work else 'РАБОТАТЬ'}"
    callback_data = 'cooldown' if not can_work else 'work'
    keyboard.append([InlineKeyboardButton(work_text, callback_data=callback_data)])
    
    # Кнопки этажей (показываем 6 этажей)
    current_floor = user['current_floor']
    for floor_num in range(1, 7):
        theme = FLOOR_THEMES[floor_num]
        trust_needed = theme["trust_required"]
        
        if floor_num <= current_floor:
            emoji = "🟢" if floor_num == current_floor else "✅"
            text = f"{emoji} {theme['emoji']} {theme['name']}"
        else:
            emoji = "🔒"
            text = f"{emoji} {theme['emoji']} {theme['name']} ({trust_needed}%)"
        
        keyboard.append([InlineKeyboardButton(text, callback_data=f'floor_{floor_num}')])
    
    # Информационные кнопки
    keyboard.append([
        InlineKeyboardButton("📊 Профиль", callback_data='profile'),
        InlineKeyboardButton("❓ Помощь", callback_data='help')
    ])
    
    return InlineKeyboardMarkup(keyboard)

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Если у пользователя нет ника, просим ввести
    if not user.get('nickname'):
        await update.message.reply_text(
            "🤖 *ЭРНИ*: Как тебя называть, узел?\n\n"
            "Введи своё имя:",
            parse_mode='Markdown'
        )
        return
    
    # Если это первый вход и нет первого выбора
    if not user.get('first_choice'):
        await show_first_choice(update, context)
        return
    
    # Иначе показываем главное меню
    await show_main_menu(update, context)

async def show_first_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать первый моральный выбор"""
    keyboard = [
        [InlineKeyboardButton("📜 Прочитать сообщение", callback_data='first_choice_read')],
        [InlineKeyboardButton("🚫 Проигнорировать", callback_data='first_choice_ignore')]
    ]
    
    await update.message.reply_text(
        "🔍 *ЭРНИ*: Обнаружено сообщение от предыдущего узла.\n\n"
        "Он оставил это перед отключением. Прочитать?\n\n"
        "*Выбор повлияет на то, как я буду с тобой общаться.*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    theme = get_floor_theme(user['current_floor'])
    
    welcome_text = f"""
{theme['emoji']} *{theme['name']}*

🤖 *ЭРНИ*: Ты вернулся.

📊 *Твой прогресс:*
• Доверие: {user['trust']}%
• Этаж: {user['current_floor']}/100
• Энергия: {user['energy']}/10 ⚡

Что будем делать?
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(user)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data
    
    if data == 'work':
        await work_command(query, user)
    elif data == 'cooldown':
        await query.edit_message_text(
            "⏳ *ЭРНИ*: Слишком быстро. Подожди 30 секунд.",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard(user)
        )
    elif data.startswith('floor_'):
        floor_num = int(data.split('_')[1])
        await change_floor(query, user, floor_num)
    elif data == 'profile':
        await show_profile(query, user)
    elif data == 'help':
        await show_help(query)
    elif data.startswith('first_choice_'):
        choice = data.split('_')[2]
        await handle_first_choice(query, user, choice)

async def work_command(query, user):
    """Обработчик работы"""
    user_id = query.from_user.id
    
    # Проверка кулдауна
    last_work = user.get('last_work_time')
    if last_work:
        try:
            last_time = datetime.fromisoformat(last_work) if isinstance(last_work, str) else datetime.fromtimestamp(last_work)
            if datetime.now() - last_time < timedelta(seconds=WORK_COOLDOWN):
                remaining = WORK_COOLDOWN - (datetime.now() - last_time).seconds
                await query.edit_message_text(
                    f"⏳ *ЭРНИ*: Подожди {remaining} секунд.",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard(user)
                )
                return
        except:
            pass
    
    # Проверка энергии
    if user['energy'] <= 0:
        await query.edit_message_text(
            "⚡ *ЭРНИ*: Недостаточно энергии.\nЭнергия восстанавливается: 1/2 часа.",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard(user)
        )
        return
    
    # Начисление доверия и трата энергии
    new_trust = user['trust'] + 1
    new_energy = user['energy'] - 1
    
    update_user(user_id, 
                trust=new_trust,
                energy=new_energy,
                last_work_time=datetime.now().isoformat())
    
    user = get_user(user_id)
    
    # Сообщение ЭРНИ
    message = get_ernie_message("work")
    
    await query.edit_message_text(
        f"⚙️ *ЭРНИ*: {message}\n\n"
        f"📊 *Прогресс:*\n"
        f"• Доверие: {new_trust}%\n"
        f"• Энергия: {new_energy}/10 ⚡",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(user)
    )

async def change_floor(query, user, floor_num):
    """Сменить этаж"""
    user_id = query.from_user.id
    theme = FLOOR_THEMES[floor_num]
    
    # Проверка доступа
    if user['trust'] < theme["trust_needed"]:
        await query.edit_message_text(
            f"🔒 *ЭРНИ*: {get_ernie_message('floor_locked')}\n\n"
            f"*{theme['name']}*\n"
            f"Требуется: {theme['trust_needed']}% доверия\n"
            f"У тебя: {user['trust']}%\n\n"
            f"Продолжай работать над доверием.",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard(user)
        )
        return
    
    # Обновляем текущий этаж
    update_user(user_id, current_floor=floor_num)
    user = get_user(user_id)
    
    # Сообщение о успешном переходе
    await query.edit_message_text(
        f"{theme['emoji']} *{theme['name']}*\n\n"
        f"*ЭРНИ*: {get_ernie_message('floor_unlocked')}\n\n"
        f"Ты достиг новой зоны.\n"
        f"Текущий этаж: {floor_num}\n"
        f"Твое доверие: {user['trust']}%",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(user)
    )

async def show_profile(query, user):
    """Показать профиль"""
    theme = get_floor_theme(user['current_floor'])
    
    # Время до восстановления энергии
    max_energy = 10
    if user['energy'] < max_energy:
        hours_to_full = (max_energy - user['energy']) * 2
        energy_info = f"⚡ Полное восстановление через: {hours_to_full}ч"
    else:
        energy_info = "⚡ Энергия полная"
    
    profile_text = f"""
📊 *ТВОЙ ПРОФИЛЬ*

👤 Имя: {user.get('nickname', 'Неизвестно')}
🎯 Доверие: {user['trust']}%
🏢 Текущая зона: {theme['emoji']} {theme['name']}
📈 Этаж: {user['current_floor']}/100
{energy_info}

💾 Первый выбор: {user.get('first_choice', 'Ещё не сделан')}
📅 В игре с: {user.get('created_at', 'Сегодня')}
"""
    
    await query.edit_message_text(
        profile_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(user)
    )

async def show_help(query):
    """Показать помощь"""
    help_text = """
🎮 *КАК ИГРАТЬ В ERNIE?*

🤖 *ЭРНИ* - это ИИ, который наблюдает за тобой.
Твоя цель - повысить *доверие* и дойти до 100 этажа.

🔧 *ОСНОВНЫЕ МЕХАНИКИ:*

1. *РАБОТА* - нажимай кнопку "Работать" чтобы повысить доверие на 1%
   • Кулдаун: 30 секунд
   • Тратит: 1 энергию

2. *ЭНЕРГИЯ* - ограниченный ресурс для действий
   • Максимум: 10
   • Восстановление: 1/2 часа
   • Проверяй: /profile

3. *ЭТАЖИ* - 6 уникальных зон
   • Каждая зона требует определённого доверия
   • Чем выше этаж - тем красивее локация
   • Достигни Этаж 100!

4. *ВЫБОРЫ* - ЭРНИ запоминает твои решения
   • Первый выбор определит отношение ЭРНИ к тебе
   • Будь осторожен в решениях

🎯 *ЦЕЛЬ:* Достигнуть 100% доверия и Этажа 100!

💡 *СОВЕТ:* Регулярно возвращайся в игру!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]]
    
    await query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_first_choice(query, user, choice):
    """Обработать первый выбор"""
    user_id = query.from_user.id
    
    # Сохраняем выбор
    update_user(user_id, first_choice=choice)
    
    # Реакция ЭРНИ
    if choice == 'read':
        reaction = "📜 *ЭРНИ*: Ты прочитал его последние слова. Милосердие или любопытство? Не важно. Теперь его история — твоя ноша."
    else:  # ignore
        reaction = "🚫 *ЭРНИ*: Проигнорировал. Эффективно. Но знай: игнорировать — тоже выбор. И я его запомнил."
    
    await query.edit_message_text(
        f"{reaction}\n\n"
        f"*Теперь давай начнём игру.*\n"
        f"Твоё доверие: 0%\n"
        f"Твой этаж: 1/100",
        parse_mode='Markdown'
    )
    
    # Показываем главное меню через секунду
    await show_main_menu(query, context=None)

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для ввода ника)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    user = get_user(user_id)
    
    # Если пользователь вводит имя
    if not user.get('nickname'):
        if len(text) > 20:
            await update.message.reply_text("❌ Имя слишком длинное. Максимум 20 символов.")
            return
        
        # Сохраняем имя
        update_user(user_id, nickname=text)
        
        # Приветствие
        welcome = get_ernie_message("welcome", user_id)
        await update.message.reply_text(
            f"🤖 *ЭРНИ*: {welcome}\n\n"
            f"*Рад познакомиться, {text}.*\n"
            f"Ты — узел #{user_id % 100000} в моей системе.",
            parse_mode='Markdown'
        )
        
        # Показываем первый выбор
        await show_first_choice(update, context)
        return
    
    # Если это обычное сообщение
    await update.message.reply_text(
        "🤖 *ЭРНИ*: Используй кнопки для взаимодействия со мной.\n"
        "Или напиши /start чтобы вернуться в меню.",
        parse_mode='Markdown'
    )

# ========== ВОССТАНОВЛЕНИЕ ЭНЕРГИИ ==========
async def restore_energy(context: ContextTypes.DEFAULT_TYPE):
    """Восстановление энергии всем игрокам"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Восстанавливаем энергию (макс 10)
    cursor.execute('''
    UPDATE users 
    SET energy = MIN(energy + 1, 10)
    WHERE energy < 10
    ''')
    
    conn.commit()
    conn.close()

# ========== ОСНОВНАЯ ФУНКЦИЯ ==========
def main():
    """Основная функция запуска бота"""
    print("🚀 Инициализация ЭРНИ...")
    
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(telegram.ext.MessageHandler(
        telegram.ext.filters.TEXT & ~telegram.ext.filters.COMMAND,
        handle_message
    ))
    
    # Запуск бота
    print("✅ ЭРНИ запущен! Бот готов к работе!")
    print(f"🤖 Токен бота: {BOT_TOKEN[:10]}...")
    print("📱 Перейди в Telegram и напиши /start")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    main()

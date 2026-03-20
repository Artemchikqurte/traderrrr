import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import datetime

# ВСТАВЬТЕ ВАШ ТОКЕН СЮДА!
TOKEN = "YOUR_BOT_TOKEN_HERE"

# Включим логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Хранилище пользователей (в реальном проекте используйте базу данных)
users_data = {}

# === КОМАНДЫ БОТА ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Приветственное сообщение с кнопками
    welcome_text = f"""
✨ *Привет, {user.first_name}!* ✨

Я ваш личный помощник! Вот что я умею:

📝 *Основные команды:*
/help - Показать это сообщение
/about - Обо мне
/time - Текущее время
/echo [текст] - Повторить текст

🎮 *Интерактивные кнопки:*
Просто нажми на кнопки ниже!

📢 *Уведомления:*
/set_notify - Включить уведомления
/stop_notify - Выключить уведомления

Чем могу помочь?
"""
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("🕐 Время", callback_data="time")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton("📊 Меню", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # Сохраняем пользователя
    if user.id not in users_data:
        users_data[user.id] = {
            'username': user.username,
            'first_name': user.first_name,
            'notify': False,
            'first_seen': datetime.datetime.now()
        }
        print(f"Новый пользователь: {user.first_name} (@{user.username})")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🤖 *Доступные команды:*

📌 *Основные:*
/start - Начать работу с ботом
/help - Показать эту справку
/about - Информация о боте

🛠 *Полезные:*
/time - Текущее время и дата
/echo [текст] - Бот повторит ваш текст
/echo bold [текст] - Жирный текст
/echo code [текст] - Текст как код

🔔 *Уведомления:*
/set_notify - Включить ежечасные уведомления
/stop_notify - Выключить уведомления

💡 *Совет:* Используйте кнопки под сообщениями для быстрого доступа!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /about"""
    about_text = """
🤖 *О боте*

Версия: 1.0
Создан: 2024
Технологии: Python + python-telegram-bot

*Возможности:*
• Интерактивные кнопки
• Ежечасные уведомления
• Простой и понятный интерфейс

*Контакты:*
По вопросам и предложениям пишите @your_username
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущее время"""
    now = datetime.datetime.now()
    time_text = f"""
🕐 *Текущее время:*
{now.strftime('%d.%m.%Y %H:%M:%S')}

📅 *День недели:* {now.strftime('%A')}
"""
    await update.message.reply_text(time_text, parse_mode='Markdown')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторить текст пользователя"""
    # Получаем текст после команды
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Напишите текст после команды!\n"
            "Пример: `/echo Привет, мир!`",
            parse_mode='Markdown'
        )
        return
    
    text = ' '.join(args)
    
    # Проверяем специальные форматы
    if text.startswith('bold '):
        formatted_text = f"*{text[5:]}*"
        await update.message.reply_text(formatted_text, parse_mode='Markdown')
    elif text.startswith('code '):
        formatted_text = f"`{text[5:]}`"
        await update.message.reply_text(formatted_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"📢 Вы сказали: {text}")

async def set_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включить уведомления"""
    user_id = update.effective_user.id
    
    if user_id in users_data:
        users_data[user_id]['notify'] = True
        await update.message.reply_text(
            "✅ Уведомления включены!\n"
            "Я буду присылать вам сообщения каждый час."
        )
    else:
        await update.message.reply_text("Сначала используйте /start")

async def stop_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выключить уведомления"""
    user_id = update.effective_user.id
    
    if user_id in users_data:
        users_data[user_id]['notify'] = False
        await update.message.reply_text(
            "❌ Уведомления выключены.\n"
            "Чтобы включить снова, используйте /set_notify"
        )
    else:
        await update.message.reply_text("Сначала используйте /start")

# === ОБРАБОТЧИКИ КНОПОК ===

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback
    
    if query.data == "time":
        now = datetime.datetime.now()
        await query.edit_message_text(
            f"🕐 {now.strftime('%H:%M:%S')}\n"
            f"📅 {now.strftime('%d.%m.%Y')}",
            parse_mode='Markdown'
        )
    
    elif query.data == "about":
        await query.edit_message_text(
            "🤖 *Бот-помощник*\n\n"
            "Создан для демонстрации возможностей Telegram ботов.\n"
            "Использует библиотеку python-telegram-bot.",
            parse_mode='Markdown'
        )
    
    elif query.data == "menu":
        keyboard = [
            [InlineKeyboardButton("🕐 Время", callback_data="time")],
            [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📋 *Главное меню*\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🕐 Время", callback_data="time")],
            [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
            [InlineKeyboardButton("📊 Меню", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✨ *Главное меню*\n\nЧем могу помочь?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

# === ФУНКЦИЯ ДЛЯ РАССЫЛКИ УВЕДОМЛЕНИЙ ===

async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет уведомления всем пользователям"""
    now = datetime.datetime.now()
    message = f"🔔 *Ежечасное уведомление*\n\nВремя: {now.strftime('%H:%M')}\n\nКак дела? Напишите что-нибудь!"
    
    for user_id, user_data in users_data.items():
        if user_data.get('notify', False):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Ошибка отправки пользователю {user_id}: {e}")

# === ЗАПУСК БОТА ===

def main():
    """Запуск бота"""
    print("🚀 Запуск бота...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("echo", echo))
    application.add_handler(CommandHandler("set_notify", set_notify))
    application.add_handler(CommandHandler("stop_notify", stop_notify))
    
    # Регистрируем обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Добавляем обработчик для текстовых сообщений (на случай если пользователь просто пишет)
    async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        await update.message.reply_text(f"📝 Вы написали: {text}\n\nИспользуйте /help для списка команд!")
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))
    
    # Настраиваем периодические уведомления (каждый час)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(send_notifications, interval=3600, first=10)
        print("✅ Периодические уведомления настроены")
    
    # Запускаем бота
    print("✅ Бот запущен!")
    print("Нажмите Ctrl+C для остановки")
    application.run_polling()

if __name__ == '__main__':
    main()

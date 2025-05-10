import logging
from telegram import Update
import sqlite3
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import random
from dotenv import load_dotenv
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CREATING_GAME, GETTING_BUDGET, GETTING_RULES, GETTING_KEY, ADD_USER = range(5)


def create_key():
    key = ''
    values = [i for i in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%&—_+=?.']
    for i in range(16):
        key += random.choice(values)
    return key


def create_db():
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            user_id INTEGER,
            room_name TEXT,
            room_budget TEXT,
            room_rules TEXT,
            room_key TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            username TEXT,
            room TEXT,
            pair TEXT
            )
    ''')
    conn.commit()
    conn.close()


def save_room(user_id, room_name, room_budget, room_rules, room_key):
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO history (user_id, room_name, room_budget, room_rules, room_key)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, room_name, room_budget, room_rules, room_key))
    conn.commit()
    conn.close()


def save_user(user_id, username, room):
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO users (user_id, username, room)
    VALUES (?, ?, ?)
    ''', (user_id, username, room))
    conn.commit()
    conn.close()


create_db()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/create - создание комнаты\n/my_rooms - история создания комнат\n/join - присоединиться")


async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ключ от комнаты:")
    return GETTING_KEY


async def handle_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text
    context.user_data['key'] = key
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    room = cur.execute(f'''SELECT room_name FROM history WHERE room_key = "{key}"''').fetchall()[0]
    context.user_data['room'] = room
    con.close()
    await update.message.reply_text("Введите свой никнейм:")
    return ADD_USER


async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    context.user_data['username'] = username
    await update.message.reply_text(f'Пользователь {username} добавлен в комнату "{context.user_data['room'][0]}"')
    save_user(update.message.from_user.id, username, context.user_data['room'][0])
    return ConversationHandler.END


async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название комнаты для игры.")
    return CREATING_GAME


async def handle_game_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_name = update.message.text
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    rooms = [i[0] for i in cur.execute(f'''SELECT room_name FROM history''').fetchall()]
    con.close()
    if room_name in rooms:
        await update.message.reply_text("Комната с таким названием уже есть. Введите другое название")
    else:
        context.user_data['room_name'] = room_name
        await update.message.reply_text("Название установлено.")
        await update.message.reply_text("Установите бюджет для подарка.")
        return GETTING_BUDGET


async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    budget = update.message.text
    context.user_data['budget'] = budget
    await update.message.reply_text(f"Бюджет установлен: {budget}")
    await update.message.reply_text("Введите правила игры:")
    return GETTING_RULES


async def handle_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = update.message.text
    context.user_data['rules'] = rules
    await update.message.reply_text(f"Правила игры установлены.")
    key = create_key()
    context.user_data['key'] = key
    await update.message.reply_text(f"Ключ для вашей комнаты: {key}.")
    await update.message.reply_text("Комната создана")
    save_room(update.message.from_user.id, context.user_data['room_name'], context.user_data['budget'],
               context.user_data['rules'], context.user_data['key'])
    return ConversationHandler.END


async def my_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = "Ваши комнаты:\n\n"
    id = update.message.from_user.id
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    rooms = [i[0] for i in cur.execute(f'''SELECT room_name FROM history WHERE user_id = {id}''').fetchall()]
    budgets = [i[0] for i in cur.execute(f'''SELECT room_budget FROM history WHERE user_id = {id}''').fetchall()]
    rules = [i[0] for i in cur.execute(f'''SELECT room_rules FROM history WHERE user_id = {id}''').fetchall()]
    keys = [i[0] for i in cur.execute(f'''SELECT room_key FROM history WHERE user_id = {id}''').fetchall()]
    con.close()

    for room, budget, rule, key in zip(rooms, budgets, rules, keys):
        history += f"Комната: {room}\nБюджет: {budget}\nПравила: {rule}\nКлюч: {key}\n\n"
    await update.message.reply_text(history)


def main():
    load_dotenv()
    application = ApplicationBuilder().token(os.getenv('TOKEN')).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('create', create_room), CommandHandler('join', join_room)],
        states={
            CREATING_GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_game_creation)],
            GETTING_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
            GETTING_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rules)],
            GETTING_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_key)],
            ADD_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('my_rooms', my_rooms))
    application.add_handler(CommandHandler('start', start))
    application.run_polling()


if __name__ == '__main__':
    main()
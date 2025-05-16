from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from database import save_room, save_user
import sqlite3
from dotenv import load_dotenv
import random
import os

load_dotenv()

CREATING_GAME, GETTING_BUDGET, GETTING_RULES, ADD_USER, ADD_IDEAS, GET_STARTED = range(6)


def create_key():
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890') for _ in range(16))


async def start(update: Update, context: CallbackContext):
    if context.args:
        key = context.args[0].strip()
        with sqlite3.connect("bot_history.db") as conn:
            cursor = conn.cursor()
            result = cursor.execute('''
                SELECT room_name FROM history WHERE room_key = ? LIMIT 1
            ''', (key,)).fetchone()
            if result:
                context.user_data['room'] = result[0]
                context.user_data['key'] = key
                await update.message.reply_text("Введите свой никнейм:")
                return ADD_USER
            else:
                await update.message.reply_text("Комната с таким ключом не найдена.")
    else:
        await update.message.reply_text(
            "/create — создать комнату\n/my_rooms — список созданных вами комнат\n/join — присоединиться к существующей комнате")


async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    context.user_data['username'] = username
    await update.message.reply_text("Расскажите о своих пожеланиях, чтобы помочь выбрать подарок")
    return ADD_IDEAS


async def handle_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ideas = update.message.text
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    existing_user = cur.execute('''
        SELECT * FROM users 
        WHERE user_id=? AND key=?
    ''', (update.message.from_user.id, context.user_data['key'])).fetchone()
    if existing_user is not None:
        save_user(update.message.from_user.id, context.user_data['username'], context.user_data['key'], ideas)
        await update.message.reply_text(
           f"Ваше имя успешно обновлено на '{context.user_data['username']}' в комнате '{context.user_data['room']}'.")
    else:
        await update.message.reply_text(f"Пользователь {context.user_data['username']} добавлен в комнату '{context.user_data['room']}'")
        save_user(update.message.from_user.id, context.user_data['username'], context.user_data['key'], ideas)
    con.close()
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
    await update.message.reply_text(f"Ссылка-ключ для вашей комнаты: https://t.me/{os.getenv('USERNAME_BOT')}?start={key}.")
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
        history += f"Комната: {room}\nБюджет: {budget}\nПравила: {rule}\nСсылка-ключ: https://t.me/{os.getenv('USERNAME_BOT')}?start={key}\n\n"
    await update.message.reply_text(history)


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название комнаты, где хотите начать игру:")
    return GET_STARTED


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass
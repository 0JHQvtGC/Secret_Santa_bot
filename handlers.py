from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from database import save_room, save_user, delete_by_key
import sqlite3
from dotenv import load_dotenv
import random
import os


load_dotenv()

CREATING_GAME, GETTING_BUDGET, GETTING_RULES, ADD_USER, ADD_IDEAS, WAITING_ROOM, DELETE_STEP_ONE, DELETE_STEP_TWO = range(8)


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
            "/start - запуск бота\n/create — создать комнату\n/delete_room -удаление комнаты\n/my_rooms — список созданных вами комнат\n/start_game - начало игры")


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
        rules = cur.execute(f"SELECT room_rules FROM history WHERE room_key='{context.user_data['key']}'").fetchall()[0][0]
        await update.message.reply_text(f"Пользователь {context.user_data['username']} добавлен в комнату '{context.user_data['room']}'")
        await update.message.reply_text("Правила игры:\n" + rules)
        save_user(update.message.from_user.id, context.user_data['username'], context.user_data['key'], ideas)
    con.close()
    return ConversationHandler.END


async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название комнаты для игры.")
    return CREATING_GAME


async def handle_game_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_name = update.message.text
    user_id = update.message.from_user.id
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM history WHERE room_name=? AND user_id=?", (room_name, user_id))
    result = cur.fetchone()
    con.close()
    if result is not None:
        await update.message.reply_text("Вы уже создавали комнату с таким названием. Введите другое название")
    else:
        context.user_data['room_name'] = room_name
        await update.message.reply_text("Название установлено.")
        await update.message.reply_text("Установите бюджет для подарка.")
        return GETTING_BUDGET


async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    budget = update.message.text
    context.user_data['budget'] = budget
    await update.message.reply_text(f"Бюджет установлен: {budget}")
    await update.message.reply_text("Введите правила игры. Также укажите в них длительность игры и локацию, где нужно оставить подарки.")
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
    id = update.message.from_user.id
    with sqlite3.connect("bot_history.db") as conn:
        cursor = conn.cursor()
        rooms = [i[0] for i in cursor.execute(f'''SELECT room_name FROM history WHERE user_id = {id}''').fetchall()]
    if len(rooms) == 0:
        await update.message.reply_text("На данный момент у Вас нет комнат, где можно начать игру. Создайте новую комнату.")
    else:
        context.user_data['user_rooms'] = rooms
        await update.message.reply_text("Введите название комнаты, где хотели бы начать игру:")
    return WAITING_ROOM


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_name = update.message.text
    id = update.message.from_user.id
    if room_name in context.user_data['user_rooms']:
        con = sqlite3.connect("bot_history.db")
        cur = con.cursor()
        started = cur.execute(f"SELECT started FROM history WHERE user_id={id} AND room_name='{room_name}'").fetchall()[0][0]
        if started == "no":
            key = cur.execute(f"SELECT room_key FROM history WHERE user_id={id} AND room_name='{room_name}'").fetchall()[0][0]
            users_data = cur.execute(f"SELECT user_id, username FROM users WHERE key = '{key}'").fetchall()
            users = [i[0] for i in users_data]
            usernames = [i[1] for i in users_data]
            if len(users) < 2:
                print(len(users))
                print(users)
                await update.message.reply_text("Недостаточно участников для начала игры")
            else:
                pairs = users[:]
                result = {}
                for person in users:
                    new_pairs = [i for i in pairs if i != person]
                    man = random.choice(new_pairs)
                    result[person] = man
                    pairs.remove(man)
                file = open("users_data.txt", "w", encoding="utf-8")
                for user in result:
                    cur.execute(f"UPDATE users SET pair='{result[user]}' WHERE user_id = {user} AND key='{key}'")
                    ideas = cur.execute(f"SELECT ideas FROM users WHERE user_id = {result[user]} AND key='{key}'").fetchall()[0][0]
                    file.write(f"{usernames[users.index(user)]} (id {user}) делает подарок {usernames[users.index(result[user])]}"
                               f" (id {users[usernames.index(usernames[users.index(result[user])])]})\n"
                               f"Пожелания {usernames[users.index(result[user])]}: {ideas}\n\n")
                    await context.bot.send_message(chat_id=user,
                                                   text=f"Игра началась. Вы должны сделать подарок пользователю"
                                                        f" {usernames[users.index(result[user])]}.\n"
                                                        f"Возможные идеи для подарка {usernames[users.index(result[user])]}: {ideas}")
                file.close()
                cur.execute(f"UPDATE history SET started='yes' WHERE room_key = '{key}'")
            con.close()
            with open("users_data.txt", 'rb') as file:
                await update.message.reply_text("Список участников игры:")
                await context.bot.send_document(id, document=file)
        else:
            await update.message.reply_text("Игра уже началась")
    else:
        await update.message.reply_text("Комната с таким названием не найдена")
    return ConversationHandler.END


async def delete_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название комнаты, которую хотите удалить:")
    return DELETE_STEP_ONE


async def handle_delete_room_step_one(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['room_name'] = update.message.text
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    existing_user = cur.execute(''' SELECT * FROM history WHERE user_id=? AND room_name=? ''',
                                (update.message.from_user.id, context.user_data['room_name'])).fetchone()
    con.close()

    if existing_user is None:
        await update.message.reply_text('Комната не найдена')
        return ConversationHandler.END
    keyboard = [[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        f'Вы уверены что хотите удалить комнату {context.user_data["room_name"]}?',
        reply_markup=reply_markup
    )
    return DELETE_STEP_TWO


async def handle_delete_room_step_two(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.lower()
    if answer == 'да':
        con = sqlite3.connect("bot_history.db")
        cur = con.cursor()
        key = cur.execute(
            f""" SELECT room_key FROM history WHERE user_id={update.message.from_user.id} AND room_name='{context.user_data['room_name']}' """).fetchall()[
            0][0]
        con.close()
        delete_by_key(key)
        await update.message.reply_text(f'Комната "{context.user_data["room_name"]}" успешно удалена.',
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    await update.message.reply_text(
        "Удаление отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from database import save_room, save_user, delete_by_key
import sqlite3
from dotenv import load_dotenv
import random
import os


load_dotenv()

CREATING_GAME, GETTING_BUDGET, GETTING_RULES, ADD_USER, ADD_IDEAS, WAITING_ROOM, DELETE_STEP_ONE, DELETE_STEP_TWO, LEAVING_ROOM = range(9)


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
            "Данный бот для организации игры Тайный Санта")


async def leave_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название комнаты, которую хотите покинуть")
    return LEAVING_ROOM


async def handle_leaving(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room = update.message.text
    id = update.message.from_user.id
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    rooms = [i[0] for i in cur.execute(f'''SELECT room_name FROM history WHERE user_id = {id}''').fetchall()]
    if room not in rooms:
        await update.message.reply_text("Комната с таким названием не найдена")
    else:
        key = cur.execute(f"SELECT room_key FROM history WHERE room_name='{room}'").fetchall()[0][0]
        cur.execute(f"DELETE FROM users WHERE key='{key}' AND user_id={id}")
        await update.message.reply_text("Вы покинули комнату " + room)
    con.close()
    return ConversationHandler.END


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
    id = update.message.from_user.id
    con = sqlite3.connect("bot_history.db")
    cur = con.cursor()
    rooms = [i[0] for i in cur.execute(f'''SELECT room_name FROM history WHERE user_id = {id}''').fetchall()]
    budgets = [i[0] for i in cur.execute(f'''SELECT room_budget FROM history WHERE user_id = {id}''').fetchall()]
    rules = [i[0] for i in cur.execute(f'''SELECT room_rules FROM history WHERE user_id = {id}''').fetchall()]
    keys = [i[0] for i in cur.execute(f'''SELECT room_key FROM history WHERE user_id = {id}''').fetchall()]
    if len(rooms) == 0:
        await update.message.reply_text("У вас нет созданных Вами комнат")
    else:
        history = "Созданные вами комнаты:\n\n"
        for room, budget, rule, key in zip(rooms, budgets, rules, keys):
            history += f"Комната: {room}\nБюджет: {budget}\nПравила: {rule}\nСсылка-ключ: https://t.me/{os.getenv('USERNAME_BOT')}?start={key}\n\n"
        await update.message.reply_text(history)
    keys = [i[0] for i in cur.execute(f'''SELECT key FROM users WHERE user_id = {id}''').fetchall()]
    if len(keys) == 0:
        await update.message.reply_text("У Вас нет комнат, где Вы являетесь участником игры")
    else:
        history = "Комнаты, в которых Вы участвуете\n\n"
        for i in keys:
            data = [i for i in cur.execute(f"SELECT room_name, room_budget, room_rules, started FROM history WHERE room_key = '{i}'").fetchall()]
            for values in data:
                history += f"Комната: {values[0]}\nБюджет: {values[1]}\nПравила: {values[2]}\n"
                if values[3] == "yes":
                    pair = cur.execute(f"SELECT pair from users where user_id={id} and key='{i}'").fetchall()[0]
                    username_pair = cur.execute(f"SELECT Username from users where user_id={pair[0]} and key='{i}'").fetchall()[0]
                    history += f"Игра началась. Вы должны сделать подарок {username_pair[0]}\n\n"
                else:
                    history += "Игра ещё не началась\n\n"
        await update.message.reply_text(history)
    con.close()


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
    room_name = update.message.text.strip()
    user_id = update.message.from_user.id
    if room_name not in context.user_data.get('user_rooms', []):
        await update.message.reply_text("Комната с таким названием не найдена.")
        return ConversationHandler.END
    conn = sqlite3.connect("bot_history.db")
    cursor = conn.cursor()
    started = cursor.execute(
        "SELECT started FROM history WHERE user_id=? AND room_name=?",
        (user_id, room_name)
    ).fetchone()
    if started and started[0].strip().lower() == "yes":
        await update.message.reply_text("Игра уже началась.")
        return ConversationHandler.END
    key = cursor.execute(
        "SELECT room_key FROM history WHERE user_id=? AND room_name=?",
        (user_id, room_name)
    ).fetchone()[0]
    users_data = cursor.execute(
        "SELECT user_id, username FROM users WHERE key=?",
        (key,)
    ).fetchall()
    if len(users_data) < 2:
        await update.message.reply_text("Недостаточно участников для начала игры.")
        return ConversationHandler.END
    users = [row[0] for row in users_data]
    usernames = dict((uid, name) for uid, name in users_data)
    pairs = users.copy()
    result = {}
    for person in users:
        available_partners = [p for p in pairs if p != person]
        partner = random.choice(available_partners)
        result[person] = partner
        pairs.remove(partner)
    stats = ""
    for user in result:
        partner_id = result[user]
        partner_username = usernames[partner_id]
        ideas = cursor.execute(
            "SELECT ideas FROM users WHERE user_id=? AND key=?",
            (partner_id, key)
        ).fetchone()[0]
        cursor.execute(
            "UPDATE users SET pair=? WHERE user_id=? AND key=?",
            (partner_id, user, key)
        )
        message = (
            f"Игра началась.\nВы должны сделать подарок пользователю "
            f"{partner_username}. Возможные идеи для подарка:\n{ideas}"
        )
        await context.bot.send_message(chat_id=user, text=message)

        stats += (
            f"{usernames[user]} (id {user}) делает подарок {partner_username} (id {partner_id}).\n"
            f"Пожелания {partner_username}: {ideas}\n\n"
        )
    filename = "users_data.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(stats)
    cursor.execute(
        "UPDATE history SET started='yes' WHERE room_key=?",
        (key,)
    )
    await update.message.reply_text("Список участников игры:")
    await context.bot.send_document(user_id, document=open(filename, 'rb'))
    os.remove(filename)
    conn.commit()
    conn.close()
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
        f'Вы уверены, что хотите удалить комнату {context.user_data["room_name"]}?',
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
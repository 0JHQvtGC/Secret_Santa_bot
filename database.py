import sqlite3


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
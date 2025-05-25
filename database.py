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
            room_key TEXT,
            started TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            username TEXT,
            key TEXT,
            ideas TEXT,
            pair TEXT
            )
    ''')
    conn.commit()
    conn.close()


def save_room(user_id, room_name, room_budget, room_rules, room_key):
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO history (user_id, room_name, room_budget, room_rules, room_key, started)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, room_name, room_budget, room_rules, room_key, "no"))
    conn.commit()
    conn.close()


def save_user(user_id, username, key, ideas, pair="no pair"):
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=? AND key=?", (user_id, key))
    existing_row = cursor.fetchone()
    if existing_row is not None:
        cursor.execute('''
            UPDATE users SET username=?, ideas=?
            WHERE user_id=? AND key=?
        ''', (username, ideas, user_id, key))
    else:
        cursor.execute('''
        INSERT INTO users (user_id, username, key, ideas, pair)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, key, ideas, pair))
    conn.commit()
    conn.close()


def delete_by_key(key):
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM history WHERE room_key=?", (key,))
        cursor.execute("DELETE FROM users WHERE key=?", (key,))
        conn.commit()
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        conn.close()


def get_info_using_user_id(user_id):
    conn = sqlite3.connect('bot_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT key FROM users WHERE user_id=? AND pair=?",
                   (user_id, 'no pair'))
    keys = [row[0] for row in cursor.fetchall()]
    if not keys:
        conn.close()
        return [], []
    placeholders = ', '.join(['?'] * len(keys))
    cursor.execute(f"SELECT room_name FROM history WHERE room_key IN ({placeholders})", tuple(keys))
    rooms = [row[0] for row in cursor.fetchall()]
    conn.close()
    return keys, rooms
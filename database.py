import sqlite3
import json
from datetime import datetime

DB_NAME = "ernie.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            nickname TEXT,
            trust_level INTEGER DEFAULT 0,
            current_floor INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 10,
            last_energy_update TIMESTAMP,
            ernie_memory TEXT DEFAULT '{}',
            last_active TIMESTAMP,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова.")

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    initial_memory = json.dumps({})
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, ernie_memory, created_at, last_active)
        VALUES (?, ?, ?, ?)
    ''', (user_id, initial_memory, now, now))
    conn.commit()
    conn.close()

def update_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    columns = []
    values = []
    for key, value in kwargs.items():
        if key == "ernie_memory" and isinstance(value, dict):
            value = json.dumps(value)
        columns.append(f"{key} = ?")
        values.append(value)
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(columns)} WHERE user_id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()

def get_memory(user_id):
    user = get_user(user_id)
    if user and user['ernie_memory']:
        return json.loads(user['ernie_memory'])
    return {}

import sqlite3
from datetime import datetime

DB_PATH = "booking.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service TEXT,
                name TEXT,
                phone TEXT,
                date TEXT,
                time TEXT,
                created_at TEXT
            )
        """)
        conn.commit()


def add_booking(user_id, service, name, phone, date, time):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bookings (user_id, service, name, phone, date, time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            service,
            name,
            phone,
            date,
            time,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()


def is_slot_taken(date, time):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM bookings
            WHERE date = ? AND time = ?
            LIMIT 1
        """, (date, time))
        return cur.fetchone() is not None


def get_user_bookings(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT service, date, time
            FROM bookings
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))
        return cur.fetchall()

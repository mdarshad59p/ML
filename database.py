"""
SQLite persistence layer for Maya's Lab Bot.
Everything (economy, language prefs, bans, feature prices, message log
for /deletelog and /lastseen) lives in one file: config.DB_PATH.

SQLite is fine for a small/medium bot on a single Render instance.
If you outgrow it later, swap this module for Postgres — every function
signature here can stay the same.
"""
import sqlite3
import time
import threading
from contextlib import contextmanager

import config

_local = threading.local()


def _connect():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


@contextmanager
def get_conn():
    if not hasattr(_local, "conn"):
        _local.conn = _connect()
    conn = _local.conn
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                lang TEXT DEFAULT 'en',
                coins INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                last_daily REAL DEFAULT 0,
                referred_by INTEGER,
                referral_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                last_seen REAL DEFAULT 0,
                joined_at REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                sent_at REAL
            );

            CREATE TABLE IF NOT EXISTS deleted_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                deleted_at REAL
            );

            CREATE TABLE IF NOT EXISTS feature_prices (
                feature TEXT PRIMARY KEY,
                price INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            );
            """
        )


# ---------- USERS ----------

def upsert_user(user_id: int, username: str | None, first_name: str | None):
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, joined_at, last_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, username, first_name, time.time(), time.time()),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
                (username, first_name, time.time(), user_id),
            )


def get_user(user_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def set_lang(user_id: int, lang: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))


def get_lang(user_id: int) -> str:
    row = get_user(user_id)
    if row and row["lang"]:
        return row["lang"]
    return config.DEFAULT_LANGUAGE


def add_coins(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))


def remove_coins(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = MAX(0, coins - ?) WHERE user_id=?", (amount, user_id)
        )


def get_coins(user_id: int) -> int:
    row = get_user(user_id)
    return row["coins"] if row else 0


def can_claim_daily(user_id: int) -> bool:
    row = get_user(user_id)
    if not row:
        return True
    return (time.time() - row["last_daily"]) >= 86400


def claim_daily(user_id: int) -> int:
    """Updates streak + last_daily, returns new streak count."""
    row = get_user(user_id)
    now = time.time()
    streak = 1
    if row and (now - row["last_daily"]) < 172800:  # claimed within last 2 days -> streak continues
        streak = row["streak"] + 1
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_daily=?, streak=? WHERE user_id=?", (now, streak, user_id)
        )
    add_coins(user_id, config.DAILY_COIN_REWARD)
    return streak


def register_referral(new_user_id: int, referrer_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT referred_by FROM users WHERE user_id=?", (new_user_id,)
        ).fetchone()
        if row and row["referred_by"] is None and referrer_id != new_user_id:
            conn.execute(
                "UPDATE users SET referred_by=? WHERE user_id=?", (referrer_id, new_user_id)
            )
            conn.execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?",
                (referrer_id,),
            )
            add_coins(referrer_id, config.REFERRAL_COIN_REWARD)
            return True
    return False


def set_ban(user_id: int, banned: bool):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))


def is_banned(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and row["is_banned"])


def all_user_ids() -> list[int]:
    with get_conn() as conn:
        return [r["user_id"] for r in conn.execute("SELECT user_id FROM users")]


def user_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]


def update_last_seen(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_seen=? WHERE user_id=?", (time.time(), user_id))


def get_last_seen(user_id: int) -> float | None:
    row = get_user(user_id)
    return row["last_seen"] if row else None


# ---------- GROUP MESSAGE LOG (best-effort, see README limitation notes) ----------

def log_message(chat_id: int, message_id: int, user_id: int, username: str | None, text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO group_messages (chat_id, message_id, user_id, username, text, sent_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, message_id, user_id, username, text, time.time()),
        )
        # keep table small: only last 500 messages per chat
        conn.execute(
            """DELETE FROM group_messages WHERE chat_id=? AND id NOT IN (
                SELECT id FROM group_messages WHERE chat_id=? ORDER BY id DESC LIMIT 500
            )""",
            (chat_id, chat_id),
        )


def get_recent_messages(chat_id: int, limit: int = 20):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM group_messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()


def log_deleted(chat_id: int, user_id: int, username: str | None, text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO deleted_log (chat_id, user_id, username, text, deleted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, username, text, time.time()),
        )


def get_deleted_log(chat_id: int, limit: int = 20):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM deleted_log WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()


# ---------- FEATURE PRICING (admin) ----------

def set_feature_price(feature: str, price: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO feature_prices (feature, price) VALUES (?, ?) "
            "ON CONFLICT(feature) DO UPDATE SET price=excluded.price",
            (feature, price),
        )


def get_feature_price(feature: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT price FROM feature_prices WHERE feature=?", (feature,)
        ).fetchone()
        return row["price"] if row else 0

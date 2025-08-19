#!/usr/bin/env python3
"""
Asterix Storage Bot – Fully Fixed & Working with Deep Links
"""

import os
import logging
import sqlite3
import datetime
from typing import List, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from rapidfuzz import process

# ------------------------------ CONFIG ------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MAIN_CHANNEL = "@FreeWebseriesBD"
BACKUP_CH = "@AsterixMovies"
FILE_CH_ID = -1003017034291

OWNER_IDS: List[int] = [5711576992]
BOT_USERNAME: Optional[str] = None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_PATH = "storage_bot.db"


# ------------------------------ Database Helpers ------------------------------
def db_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = db_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        join_date TEXT,
        banned INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        message_id INTEGER PRIMARY KEY,
        file_name TEXT,
        caption TEXT,
        type TEXT,
        downloads INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        query TEXT,
        date TEXT
    )""")
    conn.commit()
    conn.close()

def add_user(user_id: int, username: Optional[str]):
    conn = db_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
              (user_id, username, datetime.date.today().isoformat()))
    conn.commit()
    conn.close()

def is_banned(user_id: int) -> bool:
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == 1)

def add_file(msg_id: int, file_name: str, caption: str, ftype: str):
    conn = db_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO files (message_id, file_name, caption, type) VALUES (?, ?, ?, ?)",
              (msg_id, file_name, caption, ftype))
    conn.commit()
    conn.close()

def get_all_files():
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT file_name, message_id, caption, type FROM files")
    all_files = c.fetchall()
    conn.close()
    return all_files

def search_files(query: str):
    all_files = get_all_files()
    if not all_files:
        return []
    names = [f[0] for f in all_files]
    results = process.extract(query, names, limit=10, score_cutoff=40)
    matches = []
    for name, score, idx in results:
        matches.append(all_files[idx])
    return matches

def record_search(user_id: int, query: str):
    conn = db_conn()
    c = conn.cursor()
    c.execute("INSERT INTO searches (user_id, query, date) VALUES (?, ?, ?)",
              (user_id, query, datetime.date.today().isoformat()))
    conn.commit()
    conn.close()

def increment_download(mid: int):
    conn = db_conn()
    c = conn.cursor()
    c.execute("UPDATE files SET downloads = downloads + 1 WHERE message_id = ?", (mid,))
    conn.commit()
    conn.close()


# ------------------------------ Keyboard Helpers ------------------------------
async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    global BOT_USERNAME
    if not BOT_USERNAME:
        BOT_USERNAME = (await context.bot.get_me()).username
    return BOT_USERNAME

async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel: str) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
        [InlineKeyboardButton("✅ Join Backup Channel", url=f"https://t.me/{BACKUP_CH.strip('@')}")],
        [InlineKeyboardButton("🔁 I Joined", callback_data="check_joined")]
    ])

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Latest Movies", callback_data="btn_movies"),
         InlineKeyboardButton("📺 Latest Webseries", callback_data="btn_webseries")],
        [InlineKeyboardButton("🔥 Trending", callback_data="btn_trending"),
         InlineKeyboardButton("⭐ Most Downloaded", callback_data="btn_top")],
        [InlineKeyboardButton("❓ Help", callback_data="btn_help")]
    ])

def back_button_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="btn_back")]
    ])


# ------------------------------ Handlers ------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    add_user(user.id, user.username)

    bot_username = await get_bot_username(context)

    # Deep link handling
    args = context.args
    if args and args[0].startswith("file_"):
        try:
            msg_id = int(args[0].split("_")[1])
            await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=FILE_CH_ID,
                message_id=msg_id
            )
            increment_download(msg_id)
            return
        except Exception as e:
            logger.error(f"Error fetching deep link: {e}")
            await context.bot.send_message(chat_id, "❌ File not found.")
            return

    if is_banned(user.id):
        await context.bot.send_message(chat_id, "🚫 You are banned from using this bot.")
        return

    joined_main = await is_member(context, user.id, MAIN_CHANNEL)
    joined_backup = await is_member(context, user.id, BACKUP_CH)

    if not (joined_main and joined_backup):
        await context.bot.send_message(
            chat_id,
            f"⚠️ You must join the main and backup channels to use this bot.\n\n"
            f"Main: {MAIN_CHANNEL}\nBackup: {BACKUP_CH}",
            reply_markup=join_keyboard()
        )
        return

    await context.bot.send_message(
        chat_id,
        f"👋 Hello {user.first_name},\n\n"
        f"📂 Welcome to **Asterix Bot**\n"
        "🔍 Search and get movies or web series instantly.\n\n"
        "➡️ Use the menu below.",
        reply_markup=main_menu_keyboard()
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        return

    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Usage: /search <movie_name>", parse_mode=ParseMode.MARKDOWN)
        return

    record_search(user.id, query)
    results = search_files(query)
    bot_username = await get_bot_username(context)

    if not results:
        await update.message.reply_text(f"❌ No results found in DB.\nPlease check {MAIN_CHANNEL} or {BACKUP_CH}.")
        return

    kb = [[InlineKeyboardButton(f[0], url=f"https://t.me/{bot_username}?start=file_{f[1]}")] for f in results]
    await update.message.reply_text("🔍 Search results:", reply_markup=InlineKeyboardMarkup(kb))


# ✅ FIXED OWNER FORWARD HANDLER
async def owner_forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if user.id not in OWNER_IDS or update.effective_chat.type != "private":
        return

    # Use forward_origin (PTB v20+) instead of deprecated forward_from_chat
    if not msg.forward_origin or not getattr(msg.forward_origin, "chat", None):
        return
    if msg.forward_origin.chat.id != FILE_CH_ID:
        return

    original_mid = msg.forward_origin.message_id
    if not original_mid:
        await msg.reply_text("❌ No message id found.")
        return

    bot_user = await context.bot.get_me()
    deep_link = f"https://t.me/{bot_user.username}?start=file_{original_mid}"
    await msg.reply_text(f"✅ Deep-link created:\n{deep_link}\n\nShare this safely with users.")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "check_joined":
        joined_main = await is_member(context, user.id, MAIN_CHANNEL)
        joined_backup = await is_member(context, user.id, BACKUP_CH)
        if joined_main and joined_backup:
            await query.edit_message_text("✅ Thank you! Use the menu below.", reply_markup=main_menu_keyboard())
        else:
            await query.edit_message_text("⚠️ You still need to join both channels.", reply_markup=join_keyboard())
        return

    if data == "btn_back":
        await query.edit_message_text("Main Menu:", reply_markup=main_menu_keyboard())
        return

    if data in ["btn_movies", "btn_webseries", "btn_trending", "btn_top"]:
        text_map = {
            "btn_movies": f"🎬 Latest Movies:\nCheck {MAIN_CHANNEL} or {BACKUP_CH}.",
            "btn_webseries": f"📺 Latest Webseries:\nCheck {MAIN_CHANNEL} or {BACKUP_CH}.",
            "btn_trending": f"🔥 Trending:\nCheck {MAIN_CHANNEL} or {BACKUP_CH}.",
            "btn_top": f"⭐ Most Downloaded:\nCheck {MAIN_CHANNEL} or {BACKUP_CH}."
        }
        await query.edit_message_text(text_map[data], reply_markup=back_button_keyboard())
        return

    if data == "btn_help":
        help_text = (
            "ℹ️ **User Manual**\n\n"
            "• /search <name> → Search movies or webseries.\n"
            "• Click buttons to see sections (Latest Movies, Webseries, Trending, Top).\n"
            f"• Join channels: Main: {MAIN_CHANNEL}, Backup: {BACKUP_CH}."
        )
        await query.edit_message_text(help_text, reply_markup=back_button_keyboard(), parse_mode=ParseMode.MARKDOWN)


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await context.bot.send_message(update.effective_chat.id, "Send /start to begin.")


# ------------------------------ Main ------------------------------
def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Please set BOT_TOKEN environment variable!")
        return

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.FORWARDED, owner_forward_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, unknown_handler))

    logger.info("🚀 Asterix Bot started and ready!")
    app.run_polling()


if __name__ == "__main__":
    main()

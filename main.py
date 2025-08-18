#!/usr/bin/env python3
"""
Asterix Storage Bot – Fixed & Updated
"""

import os
import logging
from typing import List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ------------------------------
# CONFIG
# ------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "BOT TOKEN HERE")
MAIN_CHANNEL = "@FreeWebseriesBD"
BACKUP_CH = "@AsterixMovies"
FILE_CH_ID = -1003017034291
OWNER_IDS: List[int] = [5711576992]
BOT_USERNAME = None

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Helpers
# ------------------------------
async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel: str) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in (ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER)
    except:
        return False

def join_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
        [InlineKeyboardButton("🔁 I Joined", callback_data="check_joined")]
    ])

def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Start", callback_data="btn_start"),
         InlineKeyboardButton("🎬 Latest Movies", callback_data="btn_movies")],
        [InlineKeyboardButton("📺 Latest Webseries", callback_data="btn_webseries"),
         InlineKeyboardButton("❓ Help", callback_data="btn_help")],
    ])

# ------------------------------
# Handlers
# ------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_USERNAME
    bot = context.bot
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not BOT_USERNAME:
        me = await bot.get_me()
        BOT_USERNAME = me.username

    args = context.args
    # Check if deep-link has file
    if args and args[0].startswith("file_"):
        try:
            msg_id = int(args[0].split("_", 1)[1])
            await bot.forward_message(chat_id=chat_id, from_chat_id=FILE_CH_ID, message_id=msg_id)
            return
        except Exception as e:
            logger.error("File fetch failed: %s", e)
            await bot.send_message(chat_id=chat_id, text="❌ Unable to fetch file.")
            return

    # Default welcome
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"👋 Hello {user.first_name},\n\n"
            "📂 Welcome to **Asterix Bot**\n"
            "🔍 Search and get movies or web series instantly.\n\n"
            "➡️ Use the menu below."
        ),
        reply_markup=welcome_keyboard()
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "check_joined":
        joined_main = await is_member(context, user.id, MAIN_CHANNEL)
        joined_backup = await is_member(context, user.id, BACKUP_CH)
        if joined_main and joined_backup:
            await query.edit_message_text(
                f"✅ Thank you {user.first_name}! You joined both channels.\n\n"
                f"📂 Welcome to **Asterix Bot @{BOT_USERNAME}**",
                reply_markup=welcome_keyboard()
            )
        else:
            await query.edit_message_text(
                "⚠️ You still need to join both channels.",
                reply_markup=join_keyboard()
            )
        return

    if data == "btn_start":
        await query.edit_message_text(
            f"🔁 Menu reset.\nWelcome to **Asterix Bot @{BOT_USERNAME}**",
            reply_markup=welcome_keyboard()
        )
    elif data == "btn_movies":
        await query.edit_message_text("🎬 Latest movies coming soon.", reply_markup=join_keyboard())
    elif data == "btn_webseries":
        await query.edit_message_text("📺 Latest webseries coming soon.", reply_markup=join_keyboard())
    elif data == "btn_help":
        await query.edit_message_text(f"For help, contact admins of {MAIN_CHANNEL}.")
    else:
        await query.edit_message_text("Unknown action.")

async def owner_forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if update.effective_chat.type != "private" or user.id not in OWNER_IDS:
        return
    if not msg.forward_from_chat or msg.forward_from_chat.id != FILE_CH_ID:
        return

    original_mid = msg.forward_from_message_id
    if not original_mid:
        await msg.reply_text("❌ No message id found.")
        return

    bot_user = await context.bot.get_me()
    deep_link = f"https://t.me/{bot_user.username}?start=file_{original_mid}"
    await msg.reply_text(f"✅ Deep-link created:\n{deep_link}\n\nShare this safely with users.")

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Send /start to begin.")

# ------------------------------
# Main
# ------------------------------
def main():
    if BOT_TOKEN.startswith("YOUR_BOT_TOKEN_HERE"):
        logger.error("Please set your BOT_TOKEN first.")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.FORWARDED, owner_forward_handler))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, unknown_handler))

    logger.info("🚀 Asterix Bot started...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()

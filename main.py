#!/usr/bin/env python3
"""
Asterix Storage Bot
- Uses: python-telegram-bot v20+ (async)
- Features:
  * /start with deep-link handling (start=file_<msgid>)
  * Join-check for MAIN_CHANNEL and BACKUP_CH (forces user to join)
  * Owner-only flow: when owner forwards a file from the storage channel to the bot,
    bot generates a deep-link and posts it in the MAIN_CHANNEL
  * Buttons: Start, Latest Movies, Latest Webseries, Main Channel, Backup Channel, Help
  * Secure: owner-only operations, permission checks, safe error handling
"""

import os
import logging
from typing import List

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatMember,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ------------------------------
# CONFIG - Replace these values
# ------------------------------
# If Pella/Ai requires token in-code, paste it here.
# Otherwise set the environment variable BOT_TOKEN and the code will use it.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8227634039:AAG0_d9dNvO30I31RMTrpHDJCFJ459w4FSI")

# Public channel/usernames (use @username)
MAIN_CHANNEL = "@FreeWebseriesBD"
BACKUP_CH = "@AsterixMovies"

# Storage channel numeric ID (where files will live)
FILE_CH_ID = -1003017034291  # <-- change if needed

# Owner(s) who can generate deep links by forwarding from storage channel
OWNER_IDS: List[int] = [5711576992]

# Bot display name/handle (optional - will fetched dynamically)
BOT_USERNAME = None

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ------------------------------
# Helpers
# ------------------------------
async def is_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_username: str) -> bool:
    """
    Check if a user is a member (or admin/creator) of a public channel.
    Returns True if status in (member, administrator, creator).
    """
    try:
        member = await context.bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        return member.status in (ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER, ChatMember.CREATOR)
    except Exception as e:
        # Could be Bot not in channel or channel privacy; log and treat as not joined
        logger.warning("get_chat_member failed for %s: %s", channel_username, e)
        return False


def join_keyboard() -> InlineKeyboardMarkup:
    """Buttons prompting user to join both channels"""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Join Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
            [InlineKeyboardButton("📢 Backup/Updates", url=f"https://t.me/{BACKUP_CH.strip('@')}")],
            [InlineKeyboardButton("🔁 I Joined", callback_data="check_joined")]
        ]
    )


def welcome_keyboard() -> InlineKeyboardMarkup:
    """Main welcome keyboard with 6 buttons as requested"""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("▶️ Start", callback_data="btn_start"),
                InlineKeyboardButton("🎬 Latest Movies", callback_data="btn_movies"),
            ],
            [
                InlineKeyboardButton("📺 Latest Webseries", callback_data="btn_webseries"),
                InlineKeyboardButton("📢 Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}"),
            ],
            [
                InlineKeyboardButton("🔁 Backup Channel", url=f"https://t.me/{BACKUP_CH.strip('@')}"),
                InlineKeyboardButton("❓ Help", callback_data="btn_help"),
            ],
        ]
    )


# ------------------------------
# Handlers
# ------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start handler
    - If /start contains "file_<msgid>", attempt to forward that message from storage channel to the user
    - Otherwise perform join-check and show welcome message
    """
    global BOT_USERNAME
    bot = context.bot
    user = update.effective_user
    chat_id = update.effective_chat.id

    # fetch bot username once
    if not BOT_USERNAME:
        me = await bot.get_me()
        BOT_USERNAME = me.username if me.username else BOT_USERNAME

    # Check if start had a parameter (deep-link)
    args = context.args  # list of args passed to /start
    if args and len(args) >= 1:
        # we expect something like: file_12345
        token = args[0]
        if token.startswith("file_"):
            try:
                msg_id = int(token.split("_", 1)[1])
            except Exception:
                await bot.send_message(chat_id=chat_id, text="❌ Invalid file link.")
                return

            # Try to forward message from storage channel to user
            try:
                await bot.forward_message(chat_id=chat_id, from_chat_id=FILE_CH_ID, message_id=msg_id)
                return
            except Exception as e:
                logger.exception("Failed to forward file %s: %s", msg_id, e)
                await bot.send_message(chat_id=chat_id, text="❌ Unable to fetch file. It may have been removed or the bot lacks permission.")
                return

    # Normal start flow: check channel membership
    joined_main = await is_member_of_channel(context, user.id, MAIN_CHANNEL)
    joined_backup = await is_member_of_channel(context, user.id, BACKUP_CH)

    if not (joined_main and joined_backup):
        # Ask user to join both channels
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 Hi {user.first_name}!\n\n"
                "To use Asterix Bot and download files, please join our channels first.\n\n"
                f"Main: {MAIN_CHANNEL}\nBackup: {BACKUP_CH}\n\n"
                "After joining, press *I Joined* below."
            ),
            reply_markup=join_keyboard(),
            parse_mode="Markdown"
        )
        return

    # If both joined — welcome message + buttons
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"Welcome @{user.username or user.first_name}! 🎉\n\n"
            "Thanks for joining Asterix Bot — your friendly file storage assistant.\n"
            "Join the main and backup channels for the latest uploads and updates."
        ),
        reply_markup=welcome_keyboard()
    )


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()  # ack callback

    data = query.data
    user = query.from_user

    if data == "check_joined":
        # Re-run join-check
        joined_main = await is_member_of_channel(context, user.id, MAIN_CHANNEL)
        joined_backup = await is_member_of_channel(context, user.id, BACKUP_CH)

        if joined_main and joined_backup:
            await query.edit_message_text(
                text="✅ Thank you — you have joined both channels! Here's the bot menu.",
            )
            await context.bot.send_message(chat_id=user.id, text=f"Welcome @{user.username or user.first_name}!", reply_markup=welcome_keyboard())
        else:
            missing = []
            if not joined_main:
                missing.append("Main Channel")
            if not joined_backup:
                missing.append("Backup Channel")
            await query.edit_message_text(text=f"⚠️ You are missing: {', '.join(missing)}. Please join and press 'I Joined' again.", reply_markup=join_keyboard())
        return

    # Buttons from welcome keyboard:
    if data == "btn_start":
        await context.bot.send_message(chat_id=user.id, text="🔁 Interaction reset.", reply_markup=welcome_keyboard())
        return

    if data == "btn_movies":
        await context.bot.send_message(chat_id=user.id, text="🎬 Latest movies will be available soon. Join our channels for updates.", reply_markup=join_keyboard())
        return

    if data == "btn_webseries":
        await context.bot.send_message(chat_id=user.id, text="📺 Latest webseries will be available soon. Join our channels for updates.", reply_markup=join_keyboard())
        return

    if data == "btn_help":
        await context.bot.send_message(chat_id=user.id, text=f"Need help? Please join {MAIN_CHANNEL} and {BACKUP_CH} and message the channel admins. Or reply here and the owner will assist you.")
        return

    # Unknown callback
    await context.bot.send_message(chat_id=user.id, text="Unknown action.")


async def owner_forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    If owner forwards a message *from the storage channel* to the bot in private,
    generate a deep-link and post it to the MAIN_CHANNEL.
    This assumes owner forwards the file (not uploads) and forward_from_chat.id == FILE_CH_ID
    """
    message = update.effective_message
    user = update.effective_user

    # only respond to private forwarded messages
    if update.effective_chat.type != "private":
        return

    # only owners allowed
    if user.id not in OWNER_IDS:
        return

    # Check if message is forwarded from storage channel
    fwd = message.forward_from_chat
    if not fwd or fwd.id != FILE_CH_ID:
        # Not a forwarded-from-storage message; ignore
        return

    # the original message id in the storage channel:
    original_mid = message.forward_from_message_id
    if not original_mid:
        await message.reply_text("❌ Forward doesn't include original message id.")
        return

    # Construct deep-link: start=file_<message_id>
    # use BOT_USERNAME if available
    bot_user = await context.bot.get_me()
    bot_username = bot_user.username or BOT_USERNAME
    deep_token = f"file_{original_mid}"
    deep_link = f"https://t.me/{bot_username}?start={deep_token}"

    # Post to MAIN_CHANNEL with the deep-link
    try:
        post_text = (
            f"🎬 New file uploaded!\n\n"
            f"Click below to open in bot and download:\n\n{deep_link}\n\n"
            f"— Shared by owner."
        )
        # send to main channel (bot must be admin or allowed to post)
        await context.bot.send_message(chat_id=MAIN_CHANNEL, text=post_text)
    except Exception as e:
        logger.exception("Failed to post deep link to main channel: %s", e)
        await message.reply_text("❌ Failed to post deep link to main channel. Check bot permissions.")
        return

    # Reply to owner with the deep link and confirmation
    await message.reply_text(f"✅ Deep-link created and posted to {MAIN_CHANNEL}:\n{deep_link}")


async def unknown_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle other private messages (helpful notice)"""
    if update.effective_chat.type == "private":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Send /start to begin. If you want to generate a deep link, forward a file from the storage channel to me (owner only)."
        )


# ------------------------------
# Main
# ------------------------------
def main():
    if BOT_TOKEN.startswith("PASTE_YOUR_BOT_TOKEN_HERE"):
        logger.error("Please set your BOT_TOKEN in the script or environment variable BOT_TOKEN.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))

    # Callback query / button presses
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    # Owner forward handler: filter forwarded messages in private chats
    # We accept any forwarded messages (owner-only check inside handler)
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.FORWARDED, owner_forward_handler))

    # Unknown private text
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, unknown_message_handler))

    # Start the bot
    logger.info("🚀 Asterix Storage Bot is starting...")
    app.run_polling(allowed_updates=["message", "callback_query"])  # polling; on Pella you may run differently


if __name__ == "__main__":
    main()

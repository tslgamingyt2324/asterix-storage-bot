import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG (edit via ENV on Railway) =========
API_ID       = int(os.environ.get("API_ID", "0"))
API_HASH     = os.environ.get("API_HASH", ""))
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "@FreeWebseriesBD")
BACKUP_CH    = os.environ.get("BACKUP_CHANNEL", "@AsterixMovies")
FILE_CH_ID   = int(os.environ.get("FILE_CHANNEL_ID", "0"))   # e.g. -1001234567890
OWNER_IDS    = [int(x) for x in os.environ.get("OWNER_IDS", "").split()] if os.environ.get("OWNER_IDS") else []
# ====================================================

app = Client("asterix_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
BOT_USERNAME = None  # filled on startup


async def is_joined(user_id: int) -> bool:
    try:
        m = await app.get_chat_member(MAIN_CHANNEL, user_id)
        return m.status in ("member", "administrator", "creator")
    except:
        return False


def join_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Join Main ✅", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
         [InlineKeyboardButton("Backup/Updates", url=f"https://t.me/{BACKUP_CH.strip('@')}")]]
    )


@app.on_message(filters.command("start"))
async def start(_, msg):
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await app.get_me()
        BOT_USERNAME = me.username

    user = msg.from_user
    if not await is_joined(user.id):
        await msg.reply_text(
            f"👋 Welcome {user.first_name}!\n\n"
            f"To use this bot, please **join {MAIN_CHANNEL}** first.",
            reply_markup=join_kb()
        )
        return

    # deep-link with message_id
    parts = msg.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].isdigit():
        if FILE_CH_ID == 0:
            await msg.reply_text("⚠️ Storage not configured. Owner must set FILE_CHANNEL_ID.")
            return
        try:
            await app.copy_message(chat_id=msg.chat.id, from_chat_id=FILE_CH_ID, message_id=int(parts[1]))
        except Exception as e:
            await msg.reply_text(f"❌ File not found or bot lacks access.\n`{e}`")
        return

    await msg.reply_text(
        "📂 Asterix Storage Bot\n\n"
        "🔍 Search: `/search movie_name`\n"
        "➡️ Or tap a deep-link shared on the main channel.",
        quote=True
    )


@app.on_message(filters.command("search"))
async def search(_, msg):
    if not await is_joined(msg.from_user.id):
        await msg.reply_text("⚠️ Join the main channel to use the bot.", reply_markup=join_kb())
        return

    if FILE_CH_ID == 0:
        await msg.reply_text("⚠️ Storage not configured. Owner must set FILE_CHANNEL_ID.")
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply_text("Usage: `/search Mohanagar`", quote=True)
        return

    q = parts[1]
    async for m in app.search_messages(FILE_CH_ID, query=q, limit=1):
        await app.copy_message(msg.chat.id, FILE_CH_ID, m.id)
        return

    await msg.reply_text(f"❌ No match for **{q}**.\nStay tuned on {MAIN_CHANNEL}")


# Make deep-link by forwarding a message from storage (admin-only optional)
@app.on_message(filters.private & filters.forwarded)
async def make_deeplink_from_forward(_, msg):
    fwd = msg.forward_from_chat
    if not fwd:
        return
    if FILE_CH_ID == 0 or fwd.id != FILE_CH_ID:
        return

    # optional admin gate
    if OWNER_IDS and msg.from_user.id not in OWNER_IDS:
        return

    if not BOT_USERNAME:
        me = await app.get_me()
        username = me.username
    else:
        username = BOT_USERNAME

    mid = msg.forward_from_message_id
    link = f"https://t.me/{username}?start={mid}"
    await msg.reply_text(
        f"✅ Deep-link ready:\n{link}\n\n"
        f"Share this on {MAIN_CHANNEL}.\n(Users must join first, then tap.)"
    )


print("Asterix Storage Bot starting...")
app.run()

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG =========
API_ID       = int(os.environ.get("API_ID", "10386276"))
API_HASH     = os.environ.get("API_HASH", "eebb48fdd2b61d925217b584ec8e9859")
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8227634039:AAG0_d9dNvO30I31RMTrpHDJCFJ459w4FSI")
MAIN_CHANNEL = "@FreeWebseriesBD"   # তোমার Main Channel
BACKUP_CH    = "@AsterixMovies"     # তোমার Backup Channel
FILE_CH_ID   = -1003017034291       # Storage Channel chat_id
OWNER_IDS    = [5711576992]         # তোমার Telegram user_id
# ==========================

app = Client("asterix_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
BOT_USERNAME = None


# ---------- Helper Functions ----------
async def is_joined(user_id: int) -> bool:
    """Check if user joined main channel"""
    try:
        m = await app.get_chat_member(MAIN_CHANNEL, user_id)
        return m.status in ("member", "administrator", "creator")
    except:
        return False


def join_kb():
    """Join Buttons"""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Join Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
            [InlineKeyboardButton("📢 Backup/Updates", url=f"https://t.me/{BACKUP_CH.strip('@')}")]
        ]
    )


# ---------- Start Command ----------
@app.on_message(filters.command("start"))
async def start(_, msg):
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await app.get_me()
        BOT_USERNAME = me.username

    user = msg.from_user
    parts = msg.text.split(maxsplit=1)

    # 1️⃣ First check if user joined
    if not await is_joined(user.id):
        await msg.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            f"To use this bot, please **join {MAIN_CHANNEL}** first.",
            reply_markup=join_kb()
        )
        return

    # 2️⃣ If deep-link has file id
    if len(parts) == 2 and parts[1].isdigit():
        mid = int(parts[1])
        try:
            await app.copy_message(chat_id=msg.chat.id, from_chat_id=FILE_CH_ID, message_id=mid)
        except Exception as e:
            await msg.reply_text(f"❌ File not found.\n`{e}`")
        return

    # 3️⃣ Default welcome if no deep-link
    await msg.reply_text(
        f"👋 Hello {user.first_name},\n\n"
        "📂 **Welcome to Asterix Storage Bot**\n\n"
        "🔍 Search any movie or series from our library.\n"
        "➡️ Or simply click links shared in our channel.\n\n"
        "⚡ Powered by Asterix Team.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📢 Join Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
                [InlineKeyboardButton("❓ Help", callback_data="help"),
                 InlineKeyboardButton("ℹ️ About", callback_data="about")]
            ]
        )
    )


# ---------- Search Command ----------
@app.on_message(filters.command("search"))
async def search(_, msg):
    """Search file from storage"""
    if not await is_joined(msg.from_user.id):
        await msg.reply_text("⚠️ Join the main channel to use the bot.", reply_markup=join_kb())
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


# ---------- Owner: Forward File to Get Deep-link ----------
@app.on_message(filters.private & filters.forwarded)
async def make_deeplink_from_forward(_, msg):
    """Owner can forward a file from storage → bot gives deep-link"""
    fwd = msg.forward_from_chat
    if not fwd or fwd.id != FILE_CH_ID:
        return

    if msg.from_user.id not in OWNER_IDS:
        return

    if not BOT_USERNAME:
        me = await app.get_me()
        username = me.username
    else:
        username = BOT_USERNAME

    mid = msg.forward_from_message_id
    link = f"https://t.me/{username}?start={mid}"
    await msg.reply_text(f"✅ Deep-link ready:\n{link}\n\nShare this on {MAIN_CHANNEL}.")


print("🚀 Asterix Storage Bot starting...")
app.run()

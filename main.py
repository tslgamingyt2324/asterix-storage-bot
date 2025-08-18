import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG =========
API_ID       = int(os.environ.get("API_ID", "10386276"))
API_HASH     = os.environ.get("API_HASH", "eebb48fdd2b61d925217b584ec8e9859")
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8227634039:AAG0_d9dNvO30I31RMTrpHDJCFJ459w4FSI")
MAIN_CHANNEL = "@FreeWebseriesBD"
BACKUP_CH    = "@AsterixMovies"
FILE_CH_ID   = -1003017034291     # Storage Channel ID
OWNER_IDS    = [5711576992]       # Owner Telegram user_id
# ==========================

app = Client("asterix_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
BOT_USERNAME = None


# ========= HELPERS =========
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
        [[InlineKeyboardButton("✅ Join Main Channel", url=f"https://t.me/{MAIN_CHANNEL.strip('@')}")],
         [InlineKeyboardButton("📢 Backup/Updates", url=f"https://t.me/{BACKUP_CH.strip('@')}")]]
    )


# ========= START =========
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

    parts = msg.text.split(maxsplit=1)
    # if deep-link with message id
    if len(parts) == 2 and parts[1].isdigit():
        try:
            await app.copy_message(chat_id=msg.chat.id, from_chat_id=FILE_CH_ID, message_id=int(parts[1]))
        except Exception as e:
            await msg.reply_text(f"❌ File not found.\n`{e}`")
        return

    # Default start message
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


# ========= SEARCH =========
@app.on_message(filters.command("search"))
async def search(_, msg):
    if not await is_joined(msg.from_user.id):
        await msg.reply_text("⚠️ Join the main channel to use the bot.", reply_markup=join_kb())
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply_text("Usage: `/search Mohanagar`", quote=True)
        return

    q = parts[1]
    found = False
    async for m in app.search_messages(FILE_CH_ID, query=q, limit=5):
        await app.copy_message(msg.chat.id, FILE_CH_ID, m.id)
        found = True

    if not found:
        await msg.reply_text(f"❌ No match for **{q}**.\nStay tuned on {MAIN_CHANNEL}")


# ========= LINK GENERATOR =========
@app.on_message(filters.command("link"))
async def link_generator(_, msg):
    """Owner can generate deep-link by sending message id"""
    if msg.from_user.id not in OWNER_IDS:
        await msg.reply_text("⛔ You are not authorized to use this command.")
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.reply_text("Usage: `/link 12345`\n\nHere `12345` = file message id from storage channel.")
        return

    mid = int(parts[1])
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await app.get_me()
        BOT_USERNAME = me.username

    link = f"https://t.me/{BOT_USERNAME}?start={mid}"
    await msg.reply_text(
        f"✅ Deep-link ready:\n{link}\n\n"
        f"👉 Example Button:\n"
        f"`InlineKeyboardButton('📂 Get File', url='{link}')`"
    )


# ========= POST TO CHANNEL =========
@app.on_message(filters.command("post"))
async def post_to_channel(_, msg):
    """Owner can directly post a file button in channel"""
    if msg.from_user.id not in OWNER_IDS:
        await msg.reply_text("⛔ You are not authorized to use this command.")
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await msg.reply_text("Usage: `/post 12345 Movie Name`")
        return

    mid = int(parts[1])
    title = parts[2]

    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await app.get_me()
        BOT_USERNAME = me.username

    link = f"https://t.me/{BOT_USERNAME}?start={mid}"

    await app.send_message(
        chat_id=MAIN_CHANNEL,
        text=f"🎬 **{title}**\n\nClick below to get the file 👇",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📂 Get File", url=link)]]
        )
    )

    await msg.reply_text("✅ Posted successfully on channel!")


# ========= DEEPLINK FROM FORWARD =========
@app.on_message(filters.private & filters.forwarded)
async def make_deeplink_from_forward(_, msg):
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
    await msg.reply_text(
        f"✅ Deep-link ready:\n{link}\n\n"
        f"👉 Share this link in {MAIN_CHANNEL} with a button like:\n\n"
        f"`📂 Get File` → {link}"
    )


# ========= CALLBACK HANDLER =========
@app.on_callback_query()
async def callback(_, query):
    if query.data == "help":
        await query.message.edit_text(
            "❓ **How to Use**\n\n"
            "1. Join our main channel.\n"
            "2. Click any deep-link shared there.\n"
            "3. Or search files using `/search name`.\n\n"
            "⚡ Enjoy Unlimited Movies!",
            reply_markup=join_kb()
        )

    elif query.data == "about":
        await query.message.edit_text(
            "ℹ️ **About This Bot**\n\n"
            "📂 Asterix Storage Bot\n"
            "🔧 Developed with [Pyrogram](https://docs.pyrogram.org/)\n"
            "👨‍💻 Owner: @AsterixMovies\n\n"
            "⚡ Fast • Secure • Reliable",
            reply_markup=join_kb()
        )


print("🚀 Asterix Storage Bot starting...")
app.run()

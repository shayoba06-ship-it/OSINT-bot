# bot.py - Full working bot for Termux (token, admin id, channel, API embedded)
import logging
import json
import os
import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# ---------------- CONFIG (EMBEDDED) ----------------
BOT_TOKEN = "8408511905:AAEtJqkDkpRSMTyc_30aZsjfXOGZHIGkpdo"   # your bot token (embedded as requested)
ADMIN_ID = 8169819846                                         # admin chat id
DATA_FILE = "data.json"
DEFAULT_LIMIT = 10
FORCE_CHANNEL_DEFAULT = "@backuphaiyaarh"
API_URL_PREFIX = "https://yahu.site/api/?key=The_ajay&number="  # ✅ updated API

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- PERSISTENCE ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            logger.exception("Failed to load data file, starting fresh.")
    return {
        "users": {},
        "gift_codes": {},
        "force_channel": FORCE_CHANNEL_DEFAULT
    }

def save_data(d):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        logger.exception("Failed to save data file.")

data = load_data()

# ---------------- HELPERS ----------------
def ensure_user(uid: str):
    if uid not in data["users"]:
        data["users"][uid] = {"credits": DEFAULT_LIMIT, "stars": 0, "referred_by": None}
        save_data(data)

def add_credits(uid: str, cnt: int):
    ensure_user(uid)
    data["users"][uid]["credits"] += cnt
    save_data(data)

def reduce_credits(uid: str, cnt: int = 1):
    ensure_user(uid)
    data["users"][uid]["credits"] = max(0, data["users"][uid]["credits"] - cnt)
    save_data(data)

def get_credits(uid: str):
    ensure_user(uid)
    return data["users"][uid]["credits"]

def add_stars(uid: str, n: int):
    ensure_user(uid)
    data["users"][uid]["stars"] += n
    save_data(data)

def spend_stars(uid: str, n: int) -> bool:
    ensure_user(uid)
    if data["users"][uid]["stars"] >= n:
        data["users"][uid]["stars"] -= n
        save_data(data)
        return True
    return False

def get_stars(uid: str):
    ensure_user(uid)
    return data["users"][uid]["stars"]

def set_force_channel(ch: str):
    data["force_channel"] = ch
    save_data(data)

def get_force_channel() -> str:
    return data.get("force_channel", FORCE_CHANNEL_DEFAULT)

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    ensure_user(uid)

    if context.args:
        try:
            ref = str(int(context.args[0]))
            if ref != uid and data["users"][uid].get("referred_by") is None:
                data["users"][uid]["referred_by"] = ref
                save_data(data)
                add_stars(ref, 2)
                try:
                    await context.bot.send_message(
                        int(ref),
                        f"🎉 You earned +2 ⭐ for referring user {user.first_name}!"
                    )
                except Exception:
                    logger.warning("Could not notify referrer.")
        except Exception:
            pass

    text = (
        "🤖 Welcome to the Number-Info Bot!\n\n"
        "Commands:\n"
        "/num <number> - search number\n"
        "/balance - show searches & stars\n"
        "/addfund - spend 5 stars -> get 100 searches\n"
        "/admin - admin panel (admin only)\n"
    )
    await update.message.reply_text(text)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    ensure_user(uid)
    credits = get_credits(uid)
    stars = get_stars(uid)
    await update.message.reply_text(f"💰 Searches: {credits}\n⭐ Stars: {stars}")

async def num_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    uid = str(user.id)

    if not context.args:
        await update.message.reply_text("Usage: /num <phone_number>")
        return
    number = context.args[0].strip()

    if chat.type in ("group", "supergroup"):
        try:
            member_count = await context.bot.get_chat_member_count(chat.id)
        except Exception:
            await update.message.reply_text("⚠️ Unable to verify group size.")
            return
        if member_count < 40:
            await update.message.reply_text("❌ Group must have 40+ members.")
            return
    else:
        ch = get_force_channel()
        if ch:
            try:
                member = await context.bot.get_chat_member(ch, user.id)
                if member.status in ("left", "kicked"):
                    raise Exception("not joined")
            except Exception:
                await update.message.reply_text(f"🚨 Join our channel: {ch}")
                return

    ensure_user(uid)
    if get_credits(uid) <= 0:
        await update.message.reply_text("❌ No searches left!")
        return

    try:
        res = requests.get(API_URL_PREFIX + number, timeout=15)
        await update.message.reply_text(f"<pre>{res.text}</pre>", parse_mode=ParseMode.HTML)
        reduce_credits(uid, 1)
    except Exception as e:
        logger.exception("API failed")
        await update.message.reply_text(f"⚠️ API Error: {e}")

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user
    text = (msg.text or "").strip()
    uid = str(user.id)

    if not text or text.startswith("/"):
        return

    if chat.type in ("group", "supergroup"):
        return

    if any(ch.isdigit() for ch in text):
        ch = get_force_channel()
        if ch:
            try:
                member = await context.bot.get_chat_member(ch, user.id)
                if member.status in ("left", "kicked"):
                    raise Exception("not joined")
            except Exception:
                await update.message.reply_text(f"🚨 Join our channel: {ch}")
                return

        ensure_user(uid)
        if get_credits(uid) <= 0:
            await update.message.reply_text("❌ No searches left!")
            return

        try:
            res = requests.get(API_URL_PREFIX + text, timeout=15)
            await update.message.reply_text(f"<pre>{res.text}</pre>", parse_mode=ParseMode.HTML)
            reduce_credits(uid, 1)
        except Exception as e:
            logger.exception("API error plain message")
            await update.message.reply_text(f"⚠️ API Error: {e}")
        return

    if text in data.get("gift_codes", {}):
        g = data["gift_codes"][text]
        if uid in g.get("claimed", []):
            await update.message.reply_text("❌ Already claimed.")
            return
        if len(g.get("claimed", [])) >= g.get("max_claims", 0):
            await update.message.reply_text("❌ Max claims reached.")
            return
        ensure_user(uid)
        data["users"][uid]["credits"] += int(g.get("credits", 0))
        g.setdefault("claimed", []).append(uid)
        save_data(data)
        await update.message.reply_text(f"✅ Got {g.get('credits')} searches!")
        return

    await update.message.reply_text("❓ Send phone number or gift code.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin.")
        return
    text = (
        "⚙️ Admin commands:\n"
        "/setchannel @channelname\n"
        "/creategift CODE CREDITS MAX\n"
        "/addstars <user_id> <amount>\n"
        "/giftreport CODE\n"
        "/refreport"
    )
    await update.message.reply_text(text)

async def setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setchannel @channelname")
        return
    ch = context.args[0].strip()
    set_force_channel(ch)
    await update.message.reply_text(f"✅ Force channel set to {ch}")

async def creategift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /creategift CODE CREDITS MAX")
        return
    code = context.args[0].strip()
    credits = int(context.args[1])
    maxc = int(context.args[2])
    data.setdefault("gift_codes", {})[code] = {"credits": credits, "max_claims": maxc, "claimed": []}
    save_data(data)
    await update.message.reply_text(f"✅ Gift code {code} created.")

async def addstars_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addstars <user_id> <amount>")
        return
    target = str(context.args[0])
    amount = int(context.args[1])
    add_stars(target, amount)
    await update.message.reply_text(f"✅ Given {amount} stars to {target}")

async def giftreport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /giftreport CODE")
        return
    code = context.args[0].strip()
    if code not in data.get("gift_codes", {}):
        await update.message.reply_text("❌ No such gift code.")
        return
    claimed = data["gift_codes"][code].get("claimed", [])
    await update.message.reply_text(f"Gift {code} claimed by: {claimed}")

async def refreport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin.")
        return
    counts = {}
    for uid, info in data["users"].items():
        ref = info.get("referred_by")
        if ref:
            counts[ref] = counts.get(ref, 0) + 1
    await update.message.reply_text(f"Referral counts: {counts}")

async def addfund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    ensure_user(uid)
    if get_stars(uid) < 5:
        await update.message.reply_text("❌ Need 5 stars to get 100 searches!")
        return
    spend_stars(uid, 5)
    add_credits(uid, 100)
    await update.message.reply_text("✅ You received 100 searches! ⭐ 5 stars spent.")
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"⚡ User {update.effective_user.username or update.effective_user.first_name} ({uid}) spent 5 stars for 100 searches."
        )
    except Exception:
        logger.warning("Could not notify admin.")

# ---------------- MAIN ----------------
def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        logger.error("Please edit bot.py and set BOT_TOKEN.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("num", num_command))
    app.add_handler(CommandHandler("addfund", addfund_cmd))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("setchannel", setchannel))
    app.add_handler(CommandHandler("creategift", creategift_cmd))
    app.add_handler(CommandHandler("addstars", addstars_cmd))
    app.add_handler(CommandHandler("giftreport", giftreport_cmd))
    app.add_handler(CommandHandler("refreport", refreport_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()

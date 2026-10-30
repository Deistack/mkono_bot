import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ivas_client import IvasClient

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("TELEGRAM_GROUP_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
PRIVATE_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
IVAS_COOKIES_FILE = os.getenv("IVAS_COOKIES_FILE", "cookies.json")

GROUP_ID_FILE = os.getenv("GROUP_ID_FILE", "group_chat_id.txt")
if not GROUP_CHAT_ID and os.path.exists(GROUP_ID_FILE):
    try:
        GROUP_CHAT_ID = open(GROUP_ID_FILE).read().strip()
    except Exception:
        pass

client = None
seen_otps = set()


def get_client():
    global client
    if client is None:
        client = IvasClient(cookies_file=IVAS_COOKIES_FILE)
        client.login()
    return client


def today():
    return datetime.now().strftime("%d/%m/%Y")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_CHAT_ID
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        GROUP_CHAT_ID = str(chat.id)
        try:
            with open(GROUP_ID_FILE, "w") as f:
                f.write(GROUP_CHAT_ID)
        except Exception:
            pass
    await update.message.reply_text(
        "IVAS OTP Bot ready.\n"
        f"Chat ID: {chat.id if chat else ''}\n"
        "/numbers - list received SMS ranges\n"
        "/otps - fetch recent OTPs\n"
        "/otp <phone> <range> - fetch OTP for a number\n"
        "/refresh - reload IVAS session"
    )


async def numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = get_client()
    res = c.check_otps(from_date=today())
    if not res:
        await update.message.reply_text("Failed to fetch data from IVAS.")
        return
    lines = [f"Total: {res['count_sms']} | Paid: {res['paid_sms']} | Unpaid: {res['unpaid_sms']}"]
    for d in res.get("sms_details", []):
        lines.append(f"{d['country_number']} - count {d['count']} (paid {d['paid']}, unpaid {d['unpaid']})")
    await update.message.reply_text("\n".join(lines) if lines else "No data.")


async def otps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = get_client()
    limit = 20
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            pass
    data = c.get_all_otps(from_date=today(), limit=limit)
    if not data:
        await update.message.reply_text("No OTPs found.")
        return
    for item in data:
        await update.message.reply_text(
            f"OTP: {item['otp_message']}\nNumber: {item['phone_number']}\nRange: {item['range']}"
        )


async def otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /otp <phone_number> <range>")
        return
    phone = context.args[0]
    rng = context.args[1]
    c = get_client()
    msg = c.get_otp_message(phone, rng, from_date=today())
    if msg:
        await update.message.reply_text(f"OTP: {msg}\nNumber: {phone}")
    else:
        await update.message.reply_text("OTP not found.")


async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    client = None
    get_client()
    await update.message.reply_text("IVAS session reloaded.")


async def monitor_otps(application):
    global seen_otps
    while True:
        try:
            c = get_client()
            data = c.get_all_otps(from_date=datetime.now().strftime("%d/%m/%Y"), limit=50)
            for item in data:
                key = (item["phone_number"], item["otp_message"])
                if key in seen_otps:
                    continue
                seen_otps.add(key)
                text = (
                    "🔐 New OTP Received\n\n"
                    f"🔢 OTP: {item['otp_message']}\n"
                    f"📱 Number: {item['phone_number']}\n"
                    f"🌐 Range: {item['range']}\n"
                    f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
                    "Tap the OTP to copy!"
                )
                target = GROUP_CHAT_ID or PRIVATE_CHAT_ID
                if target:
                    await application.bot.send_message(chat_id=target, text=text)
        except Exception:
            pass
        await asyncio.sleep(2)


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("numbers", numbers))
    app.add_handler(CommandHandler("otps", otps))
    app.add_handler(CommandHandler("otp", otp))
    app.add_handler(CommandHandler("refresh", refresh))

    async def post_init(application):
        application.create_task(monitor_otps(application))

    app.post_init = post_init
    app.run_polling()


if __name__ == "__main__":
    main()

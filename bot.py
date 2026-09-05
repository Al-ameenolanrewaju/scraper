import re
import requests
import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest


# Load environment variables from .env file
load_dotenv()
RAW_KEYS = os.getenv("SERPAPI_KEYS", "")
SERPAPI_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NODE_ENGINE_URL = "http://localhost:8080/send-message"
# ----------------------------------------------------
# MAIN MENU KEYBOARD LAYOUT
# ----------------------------------------------------
def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🔍 Search Leads"), KeyboardButton("⚡ Check Status")],
        [KeyboardButton("ℹ️ Help / Usage"), KeyboardButton("📋 Search Examples")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ----------------------------------------------------
# SERPAPI GOOGLE MAPS LEAD ENGINE
# ----------------------------------------------------
def check_key_quota(api_key: str) -> bool:
    """
    Checks SerpApi free account endpoint to confirm if key has remaining credits.
    """
    try:
        res = requests.get(f"https://serpapi.com/account.json?api_key={api_key}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            # Checks plan searches left or total searches left
            left = data.get("plan_searches_left", data.get("total_searches_left", 0))
            return left > 0
    except Exception as e:
        print(f"Error checking key quota: {e}")
    return False

def get_active_serpapi_key() -> str:
    """
    Returns the first working SerpApi key with available searches.
    """
    for key in SERPAPI_KEYS:
        if check_key_quota(key):
            return key
    return None

def fetch_osm_leads(query: str, target_count: int = 100):
    """
    Lead generation engine with automatic SerpApi key failover and pagination.
    """
    if not SERPAPI_KEYS:
        print("⚠️ Warning: No SERPAPI_KEYS configured in .env file.")
        return []

    active_key = get_active_serpapi_key()
    if not active_key:
        print("❌ All configured SerpApi keys have exhausted their monthly quota.")
        return []

    leads = []
    seen_phones = set()
    start_offset = 0

    while len(leads) < target_count and start_offset < 60:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_maps",
            "q": f"{query} Nigeria",
            "type": "search",
            "gl": "ng",
            "hl": "en",
            "start": start_offset,
            "api_key": active_key
        }

        try:
            response = requests.get(url, params=params, timeout=15)

            # Switch key if limit is reached during search (HTTP 429 Too Many Requests or 403 Forbidden)
            if response.status_code in (403, 429):
                print(f"⚠️ Key exhausted (HTTP {response.status_code}). Rotating to next key...")
                active_key = get_active_serpapi_key()
                if not active_key:
                    print("❌ No remaining active keys available.")
                    break
                params["api_key"] = active_key
                response = requests.get(url, params=params, timeout=15)

            if response.status_code != 200:
                print(f"SerpApi Error Status: {response.status_code}")
                break

            data = response.json()
            local_results = data.get("local_results", [])

            if not local_results:
                break

            for place in local_results:
                if len(leads) >= target_count:
                    break

                business_name = place.get("title", query.title())
                raw_phone = place.get("phone")

                if raw_phone:
                    clean_digits = re.sub(r'\D', '', raw_phone)

                    if clean_digits.startswith('0') and len(clean_digits) == 11:
                        clean_digits = '234' + clean_digits[1:]

                    if len(clean_digits) == 13 and clean_digits.startswith('234'):
                        if clean_digits not in seen_phones:
                            seen_phones.add(clean_digits)
                            leads.append({
                                "name": business_name,
                                "phone": clean_digits
                            })

            start_offset += 20

        except Exception as e:
            print(f"SerpApi Exception: {e}")
            break

    print(f"Total Verified Leads Fetched for '{query}': {len(leads)}")
    return leads
# ----------------------------------------------------
# TELEGRAM BOT HANDLERS
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Automated Lead Gen & WhatsApp Outreach Bot*\n\n"
        "Welcome! Use the menu below to navigate.\n\n"
        "💡 *Quick Start:* Tap *🔍 Search Leads* or type `/find <category> <location>`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.post(NODE_ENGINE_URL, json={}, timeout=5)
        status_text = "🟢 *WhatsApp Engine Bridge:* ONLINE\nReady to deliver WhatsApp outreach messages."
    except Exception:
        status_text = "🔴 *WhatsApp Engine Bridge:* OFFLINE\nMake sure `node server.js` is running."

    await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Bot Usage Instructions*\n\n"
        "1️⃣ **Find Leads:** Type `/find <category> <location>`\n"
        "2️⃣ **Send Pitch:** Click the *📤 Send WhatsApp Pitch* button on any lead.\n"
        "3️⃣ **Check Engine:** Use `/status` to confirm Node.js WhatsApp engine connectivity."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


async def show_examples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    examples_text = (
        "📋 *Search Command Examples*\n\n"
        "• `/find hotel ede`\n"
        "• `/find restaurant abuja`\n"
        "• `/find real estate lekki`\n"
        "• `/find pharmacy osogbo`"
    )
    await update.message.reply_text(examples_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


async def find_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/find <category> [location]`\n_Example: `/find hotel ede`_",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Searching live Nigerian leads for *{query}*...", parse_mode="Markdown")

    leads = fetch_osm_leads(query)

    if not leads:
        await update.message.reply_text("❌ No leads found with valid phone numbers. Try another keyword or location.")
        return

    for idx, lead in enumerate(leads):
        phone = lead['phone']
        msg = (
            f"🎯 *Lead #{idx + 1}*\n"
            f"👤 *Business Name:* {lead['name']}\n"
            f"📞 *Phone:* `+{phone}`"
        )
        keyboard = [
            [InlineKeyboardButton("📤 Send WhatsApp Pitch", callback_data=f"send:{phone}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("send:"):
        target_phone = data.split(":")[1]

        pitch_text = (
            "Hello! My name is Al-ammen olanrewaju ].\n\n"
            "I noticed your business online and wanted to reach out because we help "
            "businesses like yours implement automated solution workflows to increase customer bookings. "
            "Would you be open to a quick chat about how this works?"
        )

        await query.edit_message_text(f"⏳ Dispatching WhatsApp pitch to `+{target_phone}`...", parse_mode="Markdown")

        try:
            payload = {"phone": target_phone, "message": pitch_text}
            res = requests.post(NODE_ENGINE_URL, json=payload, timeout=15)
            res_data = res.json()

            if res.status_code == 200 and res_data.get("success"):
                await query.message.reply_text(
                    f"✅ *Success!* Pitch delivered via WhatsApp to `+{target_phone}`.",
                    parse_mode="Markdown"
                )
            else:
                err_msg = res_data.get("error", "Unknown server error")
                await query.message.reply_text(
                    f"⚠️ *Delivery Failed (`+{target_phone}`):*\n{err_msg}",
                    parse_mode="Markdown"
                )
        except Exception as e:
            await query.message.reply_text(
                f"❌ *Connection Error:* Node.js engine unreachable.\n`{str(e)}`",
                parse_mode="Markdown"
            )


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔍 Search Leads":
        await update.message.reply_text(
            "Please type your search using the format:\n`/find <category> <location>`\n\n_Example: `/find hotel ede`_",
            parse_mode="Markdown"
        )
    elif text == "⚡ Check Status":
        await check_status(update, context)
    elif text == "ℹ️ Help / Usage":
        await show_help(update, context)
    elif text == "📋 Search Examples":
        await show_examples(update, context)


# ----------------------------------------------------
# NATIVE TELEGRAM MENU INITIALIZATION
# ----------------------------------------------------
async def post_init(application):
    commands = [
        BotCommand("start", "Open main menu"),
        BotCommand("find", "Search leads (e.g. /find hotel ede)"),
        BotCommand("status", "Check WhatsApp bridge status"),
        BotCommand("help", "View bot instructions"),
        BotCommand("examples", "View search command examples")
    ]
    await application.bot.set_my_commands(commands)


# ----------------------------------------------------
# INITIALIZATION
# ----------------------------------------------------
def main():
    request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0)

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find_leads))
    app.add_handler(CommandHandler("status", check_status))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("examples", show_examples))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_text))

    print("Telegram Control Panel with Menu UI is online!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
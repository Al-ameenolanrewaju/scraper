import re
import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# Load environment variables from .env file
load_dotenv()
RAW_KEYS = os.getenv("SERPAPI_KEYS", "")
SERPAPI_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NODE_ENGINE_URL = "http://localhost:8080"  # Base URL for Node.js engine

# Conversation States for Pairing Workflow
WAITING_FOR_PAIRING_PHONE = 1

# ----------------------------------------------------
# MAIN MENU KEYBOARD LAYOUT
# ----------------------------------------------------
def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🔍 Search Leads"), KeyboardButton("🔗 Pair WhatsApp")],
        [KeyboardButton("⚡ Check Status"), KeyboardButton("ℹ️ Help / Usage")],
        [KeyboardButton("📋 Search Examples")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ----------------------------------------------------
# SERPAPI GOOGLE MAPS LEAD ENGINE
# ----------------------------------------------------
def check_key_quota(api_key: str) -> bool:
    try:
        res = requests.get(f"https://serpapi.com/account.json?api_key={api_key}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            left = data.get("plan_searches_left", data.get("total_searches_left", 0))
            return left > 0
    except Exception as e:
        print(f"Error checking key quota: {e}")
    return False

def get_active_serpapi_key() -> str:
    for key in SERPAPI_KEYS:
        if check_key_quota(key):
            return key
    return None

def fetch_osm_leads(query: str, target_count: int = 100):
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
        "💡 *Quick Start:*\n"
        "• Tap *🔗 Pair WhatsApp* to link your WhatsApp account.\n"
        "• Tap *🔍 Search Leads* or type `/find <category> <location>` to gather business contacts."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


# ----------------------------------------------------
# WHATSAPP PAIRING CONVERSATION WORKFLOW
# ----------------------------------------------------
async def pair_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton(text="📱 Share Phone Number", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "🔗 *WhatsApp Authorization*\n\n"
        "Please share your phone number using the button below or type it manually "
        "with your country code (e.g., `2348000000000`).",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return WAITING_FOR_PAIRING_PHONE


async def handle_pairing_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone_number = update.message.contact.phone_number
    else:
        phone_number = update.message.text.strip()

    clean_phone = re.sub(r'\D', '', phone_number)
    if clean_phone.startswith('0') and len(clean_phone) == 11:
        clean_phone = '234' + clean_phone[1:]

    if len(clean_phone) < 10:
        await update.message.reply_text(
            "❌ Invalid phone number format. Please enter a valid number with country code (e.g., `2348000000000`)."
        )
        return WAITING_FOR_PAIRING_PHONE

    status_msg = await update.message.reply_text(
        f"🔄 Requesting pairing code for `+{clean_phone}` from Node.js engine...",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

    try:
        response = requests.get(
            f"{NODE_ENGINE_URL}/pair-code",
            params={"phone": clean_phone},
            timeout=15
        )
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            code = data.get("pairingCode")
            message_text = (
                f"✅ *WhatsApp Pairing Code Generated*\n\n"
                f"Phone: `+{clean_phone}`\n"
                f"Your Code: `{code}`\n\n"
                f"1️⃣ Open *WhatsApp* on your phone\n"
                f"2️⃣ Go to *Linked Devices* → *Link a Device*\n"
                f"3️⃣ Tap *'Link with phone number instead'*\n"
                f"4️⃣ Enter the code above."
            )
            await status_msg.edit_text(message_text, parse_mode="Markdown")
        else:
            err_msg = data.get("error", "Failed to generate pairing code.")
            await status_msg.edit_text(f"❌ *Pairing Error:* {err_msg}", parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text(
            f"⚠️ *Connection Error:* Node.js engine unreachable.\n`{str(e)}`",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cancel_pairing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pairing canceled.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.get(f"{NODE_ENGINE_URL}/", timeout=5)
        if res.status_code == 200:
            status_text = "🟢 *WhatsApp Engine Bridge:* ONLINE\nReady to deliver WhatsApp outreach messages."
        else:
            status_text = "🟡 *WhatsApp Engine Bridge:* RESPONDING WITH ERROR"
    except Exception:
        status_text = "🔴 *WhatsApp Engine Bridge:* OFFLINE\nMake sure `node server.js` is running."

    await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Bot Usage Instructions*\n\n"
        "1️⃣ **Link WhatsApp:** Tap *🔗 Pair WhatsApp* or type `/pair` to get an 8-digit linking code.\n"
        "2️⃣ **Find Leads:** Type `/find <category> <location>`\n"
        "3️⃣ **Send Pitch:** Click *📤 Send WhatsApp Pitch* on any lead card.\n"
        "4️⃣ **Check Engine:** Use `/status` to confirm Node.js WhatsApp engine connectivity."
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
            "Hello! My name is Al-ameen olanrewaju\n\n"
            "I'm a Developer. I noticed your business online and wanted to reach out because we help "
            "businesses like yours implement automated solution workflows to increase customer bookings. "
            "Would you be open to a quick chat about how this works?"
        )

        await query.edit_message_text(f"⏳ Dispatching WhatsApp pitch to `+{target_phone}`...", parse_mode="Markdown")

        try:
            payload = {"phone": target_phone, "message": pitch_text}
            res = requests.post(f"{NODE_ENGINE_URL}/send-message", json=payload, timeout=15)
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
        BotCommand("pair", "Request WhatsApp 8-digit pairing code"),
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

    # Conversation handler for Pairing Code
    pairing_conv = ConversationHandler(
        entry_points=[
            CommandHandler("pair", pair_start),
            MessageHandler(filters.Regex("^🔗 Pair WhatsApp$"), pair_start)
        ],
        states={
            WAITING_FOR_PAIRING_PHONE: [
                MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), handle_pairing_phone)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_pairing)]
    )

    app.add_handler(pairing_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find_leads))
    app.add_handler(CommandHandler("status", check_status))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("examples", show_examples))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_text))

    print("Telegram Control Panel with WhatsApp Pairing UI is online!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
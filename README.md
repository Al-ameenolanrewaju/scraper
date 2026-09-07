
```markdown
 🤖 Automated WhatsApp Lead Generation & Telegram Control Panel

An end-to-end client acquisition system. Search live business leads via SerpApi (Google Maps) and dispatch customized sales pitches directly to WhatsApp prospects via a secure, rate-limited Baileys Node.js engine—controlled seamlessly through a Telegram bot.



 🏗️ System Architecture

```text
┌─────────────────┐       Commands / Callbacks      ┌─────────────────┐
│                 ├───────────────────────────────►│                 │
│  Telegram App   │                                │ Python Bot      │
│                 │◄───────────────────────────────┤ (Control Panel) │
└─────────────────┘       Status & Code Msgs       └────────┬────────┘
                                                            │
                                                   HTTP /   │ JSON
                                                REST API    │ Payload
                                                            ▼
┌─────────────────┐        WhatsApp Web API         ┌─────────────────┐
│  WhatsApp App   │◄───────────────────────────────┤ Node.js Engine  │
│ (Target Leads)  │                                │ (Baileys Core)  │
└─────────────────┘                                └─────────────────┘

```



## 📁 Repository Structure

```text
whatsapp-lead-bot/
├── README.md                 # Complete system guide
├── node-engine/              # WhatsApp Baileys Bridge
│   ├── package.json
│   ├── server.js             # Express API with queue & rate limiting
│   └── .env.example
└── telegram-bot/             # Python Control Panel
    ├── requirements.txt      # Python dependencies
    ├── bot.py                # Main Telegram bot controller
    └── .env.example

```

---

## 🚀 Quick Start Guide

### Prerequisites

* **Node.js:** v18.0.0 or higher
* **Python:** v3.10 or higher
* **SerpApi Key:** Free or paid account at [serpapi.com](https://serpapi.com/?utm_source=gemini)
* **Telegram Bot Token:** Obtained via [@BotFather](https://t.me/BotFather?utm_source=gemini)

---

### Step 1: Environment Setup

Copy `.env.example` to `.env` inside `telegram-bot/`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
SERPAPI_KEYS=key_1,key_2,key_3
NODE_ENGINE_URL=http://localhost:8080

```

---

### Step 2: Install Dependencies

#### Node.js Engine

```bash
cd node-engine
npm install

```

#### Python Control Panel

```bash
cd telegram-bot
python -m venv venv

# On Linux/macOS:
source venv/bin/activate  

# On Windows:
venv\Scripts\activate

pip install -r requirements.txt

```

---

### Step 3: Launch

Run both servers in separate terminal windows:

**Terminal 1 (Node.js Engine):**

```bash
cd node-engine
npm start

```

**Terminal 2 (Telegram Bot):**

```bash
cd telegram-bot
python bot.py

```

---

## 📱 How to Use

1. Open your bot in **Telegram** and tap `/start`.
2. **Link WhatsApp Account:**
* Tap **`🔗 Pair WhatsApp`** or type `/pair`.
* Share your phone number (e.g., `2348000000000`).
* Enter the returned 8-digit pairing code into **WhatsApp** → **Linked Devices** → **Link with phone number instead**.


3. **Search Business Leads:**
* Type `/find <category> <location>` (e.g., `/find hotel ede` or `/find real estate lekki`).


4. **Dispatch Outreach:**
* Click **`📤 Send WhatsApp Pitch`** under any lead card. The engine queues and delivers your custom message with rate limits.



---

## 🛡️ Anti-Ban Rate Limits

| Layer | Type | Delay Buffer | Purpose |
| --- | --- | --- | --- |
| **Python Handler** | Random Pause | **3.0s – 6.0s** | Prevents rapid user clicks |
| **Node.js Engine** | Execution Queue | **10.0s – 15.0s** | Controls dispatch speed to WhatsApp servers |

---

## 📄 License

MIT License - Free for personal and commercial use.

```



 How to Package Everything into a ZIP for Selar

1. Create a folder on your computer named `whatsapp-lead-bot`.
2. Create two subfolders inside it: `node-engine` and `telegram-bot`.
3. Put `server.js` and `package.json` inside `node-engine`.
4. Put `bot.py`, `requirements.txt`, and `.env.example` inside `telegram-bot`.
5. Put the `README.md` text above into a file named `README.md` in the main `whatsapp-lead-bot` folder.
6. Right-click the `whatsapp-lead-bot` folder and select **Compress to ZIP**.
7. Upload that `.zip` file directly to **Selar** when creating your product listing.

```
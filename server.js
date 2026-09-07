const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const express = require('express');

const app = express();
app.use(express.json());

// Async delay helper
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Centralized message queue
let isProcessingQueue = false;
const messageQueue = [];

const PORT = process.env.PORT || 8080;
let isReady = false;
let sock;

async function connectToWhatsApp() {
    // Stores auth keys in local folder 'baileys_auth_info'
    const { state, saveCreds } = await useMultiFileAuthState('baileys_auth_info');

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false, // QR code generation disabled
        browser: ['Ubuntu', 'Chrome', '20.0.04']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;

        if (connection === 'close') {
            isReady = false;
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = (statusCode !== DisconnectReason.loggedOut);
            console.log(`Connection closed (code ${statusCode}). Reconnecting: ${shouldReconnect}`);

            if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === 'open') {
            console.log('✅ WhatsApp Engine successfully connected via Baileys!');
            isReady = true;
        }
    });
}

// 8-Digit Pairing Code Route (e.g., /pair-code?phone=2348000000000)
app.get('/pair-code', async (req, res) => {
    const { phone } = req.query;

    if (!phone) {
        return res.status(400).json({
            success: false,
            error: 'Provide a phone number parameter. Example: /pair-code?phone=2348000000000'
        });
    }

    if (!sock) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp socket is initializing. Try again in 5 seconds.'
        });
    }

    try {
        let cleanPhone = phone.toString().replace(/\D/g, '');
        if (cleanPhone.startsWith('0') && cleanPhone.length === 11) {
            cleanPhone = '234' + cleanPhone.substring(1);
        }

        // Request pairing code directly from Baileys socket
        const code = await sock.requestPairingCode(cleanPhone);

        console.log(`🔑 Pairing code generated for +${cleanPhone}: ${code}`);
        return res.json({
            success: true,
            phone: cleanPhone,
            pairingCode: code
        });
    } catch (err) {
        console.error('❌ Failed to generate pairing code:', err.message);
        return res.status(500).json({ success: false, error: err.message });
    }
});

// Outreach Message Endpoint (compatible with Python bot)
app.post('/send-message', (req, res) => {
  const { phone, message } = req.body;

  if (!phone || !message) {
    return res.status(400).json({ success: false, error: 'Phone and message required.' });
  }

  // Push to queue and return connection immediately or wait in queue
  messageQueue.push({ phone, message, res });
  processQueue();
});

async function processQueue() {
  if (isProcessingQueue || messageQueue.length === 0) return;
  isProcessingQueue = true;

  const currentTask = messageQueue.shift();

  try {
    const formattedPhone = `${currentTask.phone}@s.whatsapp.net`;

    // Execute Baileys send message
    await sock.sendMessage(formattedPhone, { text: currentTask.message });

    currentTask.res.json({ success: true, message: 'Message delivered to WhatsApp.' });

    // Node-level safety delay: Wait a random 10 to 15 seconds before processing next message
    const queueDelay = Math.floor(Math.random() * 5000) + 10000; // 10,000ms - 15,000ms
    console.log(`[Queue] Waiting ${(queueDelay / 1000).toFixed(1)}s before next dispatch...`);
    await delay(queueDelay);

  } catch (err) {
    console.error('[Queue Error]', err);
    if (!currentTask.res.headersSent) {
      currentTask.res.status(500).json({ success: false, error: err.message });
    }
  } finally {
    isProcessingQueue = false;
    processQueue(); // Process next item in line
  }
}

app.get('/', (req, res) => {
    res.json({
        status: 'online',
        connected: isReady
    });
});

app.listen(PORT, () => {
    console.log(`🚀 Node WhatsApp Engine listening on port ${PORT}`);
    connectToWhatsApp();
});
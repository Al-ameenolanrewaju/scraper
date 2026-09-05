const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
    }
});

let isReady = false;

// 1. QR Code Event
client.on('qr', (qr) => {
    console.log('--- SCAN THIS QR CODE IN RENDER LOGS ---');
    qrcode.generate(qr, { small: true });
});

// 2. Ready Event (Correctly sets isReady flag)
client.on('ready', () => {
    isReady = true;
    console.log('✅ WhatsApp Web Client is Ready!');
});

// 3. Status Tracking Events
client.on('auth_failure', (msg) => {
    isReady = false;
    console.error('❌ Auth failure:', msg);
});

client.on('disconnected', (reason) => {
    isReady = false;
    console.warn('⚠️ WhatsApp Web disconnected:', reason);
});

client.on('loading_screen', (percent, message) => {
    console.log(`⏳ Loading WhatsApp Web: ${percent}% - ${message}`);
});

// 4. Outreach Message Dispatch Endpoint
app.post('/send-message', async (req, res) => {
    const { phone, message } = req.body;

    // Check if engine is initialized
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp engine is still synchronizing or not logged in. Please wait.'
        });
    }

    if (!phone || !message) {
        return res.status(400).json({
            success: false,
            error: 'Phone and message are required parameters.'
        });
    }

    try {
        // Sanitize phone input
        let formattedPhone = phone.toString().replace(/\D/g, '');
        if (formattedPhone.startsWith('0') && formattedPhone.length === 11) {
            formattedPhone = '234' + formattedPhone.substring(1);
        }

        // Verify account exists on WhatsApp before attempting delivery
        const numberDetails = await client.getNumberId(formattedPhone);

        if (!numberDetails) {
            console.log(`⚠️ Number +${formattedPhone} is not registered on WhatsApp.`);
            return res.status(404).json({
                success: false,
                error: `Number +${formattedPhone} is not registered on WhatsApp.`
            });
        }

        // Dispatch outreach message
        await client.sendMessage(numberDetails._serialized, message);
        console.log(`📩 Pitch successfully sent to +${formattedPhone}`);
        return res.json({ success: true, recipient: formattedPhone });

    } catch (err) {
        console.error('❌ Failed to send message:', err.message);
        return res.status(500).json({ success: false, error: err.message });
    }
});

// Single Client Initialization
client.initialize();

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
    console.log(`🚀 Node WhatsApp Engine listening on port ${PORT}`);
});
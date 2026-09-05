const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(), // or RemoteAuth
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',      // Uses /tmp instead of /dev/shm (prevents memory crash)
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',             // Conserves CPU on cloud instances
            '--disable-gpu'
        ],
        timeout: 60000 // Increase browser connection timeout to 60s
    },
    qrMaxRetries: 5 // Allows the QR code to regenerate without failing immediately
});

let isReady = false;

// 1. QR Code Event
const QRCode = require('qrcode');
let latestQr = '';

client.on('qr', async (qr) => {
    latestQr = await QRCode.toDataURL(qr);
    console.log('New QR generated. Visit /qr on your Render URL.');
});

app.get('/qr', (req, res) => {
    if (!latestQr) return res.send('<h3>QR Code not ready or already linked. Refresh in a few seconds.</h3>');
    res.send(`<div style="display:flex;justify-content:center;align-items:center;height:100vh;"><img src="${latestQr}" style="width:300px;"/></div>`);
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
const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const QRCode = require('qrcode');

const app = express();
app.use(express.json());

let isReady = false;
let latestQr = '';

// Configure Client with extreme memory limits for Render containers
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: "render-session"
    }),
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.3000.1014587000-alpha.html',
    },
    qrMaxRetries: 5,
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',             // Conserves CPU on single-core instances
            '--disable-gpu',
            '--js-flags="--max-old-space-size=256"' // Hard cap Chrome V8 memory at 256MB
        ],
        timeout: 120000
    }
});

// 1. QR Code Event
client.on('qr', async (qr) => {
    latestQr = await QRCode.toDataURL(qr);
    console.log('New QR generated. Visit /qr on your Render URL.');
});

app.get('/qr', (req, res) => {
    if (isReady) {
        return res.send(`
            <div style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#111;color:#fff;">
                <h2>✅ WhatsApp Web Client is connected and active!</h2>
            </div>
        `);
    }

    if (!latestQr) {
        return res.send(`
            <div style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#111;color:#fff;">
                <h3>QR Code generating or loading... Refresh in a few seconds.</h3>
            </div>
        `);
    }

    res.send(`
        <div style="display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#111;color:#fff;">
            <h2 style="margin-bottom:20px;">Scan with WhatsApp</h2>
            <img src="${latestQr}" style="width:300px;height:300px;border-radius:12px;background:#fff;padding:10px;"/>
        </div>
    `);
});

// 2. Ready Event
client.on('ready', () => {
    isReady = true;
    latestQr = ''; // Clear stale QR string once authenticated
    console.log('✅ WhatsApp Web Client is Ready!');
});

// 3. Status Tracking Events
client.on('auth_failure', (msg) => {
    isReady = false;
    latestQr = '';
    console.error('❌ Auth failure:', msg);
});

client.on('disconnected', (reason) => {
    isReady = false;
    latestQr = '';
    console.warn('⚠️ WhatsApp Web disconnected:', reason);
});

client.on('loading_screen', (percent, message) => {
    console.log(`⏳ Loading WhatsApp Web: ${percent}% - ${message}`);
});

// 4. Outreach Message Dispatch Endpoint
app.post('/send-message', async (req, res) => {
    const { phone, message } = req.body;

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

// Base Route
app.get('/', (req, res) => {
    res.send('WhatsApp Engine Service is running.');
});

// Start Client and Express App
client.initialize();

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
    console.log(`🚀 Node WhatsApp Engine listening on port ${PORT}`);
});
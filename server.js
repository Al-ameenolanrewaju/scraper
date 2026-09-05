const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const express = require('express');
const QRCode = require('qrcode');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8080;
let latestQr = '';
let isReady = false;
let sock;

async function connectToWhatsApp() {
    // Stores auth keys in local folder 'baileys_auth_info'
    const { state, saveCreds } = await useMultiFileAuthState('baileys_auth_info');

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
        browser: ['Render Engine', 'Chrome', '1.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            latestQr = await QRCode.toDataURL(qr);
            isReady = false;
            console.log('New Baileys QR Code generated. Visit /qr to scan.');
        }

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
            latestQr = '';
        }
    });
}

// QR Code route
app.get('/qr', (req, res) => {
    if (isReady) {
        return res.send('<h2 style="font-family:sans-serif;text-align:center;margin-top:50px;color:#00ff88;">✅ WhatsApp is connected and active!</h2>');
    }
    if (!latestQr) {
        return res.send('<h2 style="font-family:sans-serif;text-align:center;margin-top:50px;">QR code generating... Refresh in 5 seconds.</h2>');
    }
    res.send(`
        <html>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#111;margin:0;">
                <div style="text-align:center;background:#fff;padding:20px;border-radius:12px;">
                    <h3 style="font-family:sans-serif;color:#333;margin-bottom:15px;">Scan with WhatsApp</h3>
                    <img src="${latestQr}" style="width:280px;height:280px;"/>
                </div>
            </body>
        </html>
    `);
});

// Outreach Message Endpoint (compatible with Python bot)
app.post('/send-message', async (req, res) => {
    const { phone, message } = req.body;

    if (!isReady || !sock) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp engine is still synchronizing or not logged in.'
        });
    }

    if (!phone || !message) {
        return res.status(400).json({
            success: false,
            error: 'Phone and message are required parameters.'
        });
    }

    try {
        let formattedPhone = phone.toString().replace(/\D/g, '');
        if (formattedPhone.startsWith('0') && formattedPhone.length === 11) {
            formattedPhone = '234' + formattedPhone.substring(1);
        }

        const jid = `${formattedPhone}@s.whatsapp.net`;
        await sock.sendMessage(jid, { text: message });

        console.log(`📩 Pitch successfully sent to +${formattedPhone}`);
        return res.json({ success: true, recipient: formattedPhone });

    } catch (err) {
        console.error('❌ Failed to send message:', err.message);
        return res.status(500).json({ success: false, error: err.message });
    }
});

app.get('/', (req, res) => {
    res.send('WhatsApp Baileys Engine Running.');
});

app.listen(PORT, () => {
    console.log(`🚀 Node WhatsApp Engine listening on port ${PORT}`);
    connectToWhatsApp();
});
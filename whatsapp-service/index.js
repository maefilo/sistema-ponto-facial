require("dotenv").config();
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require("@whiskeysockets/baileys");
const { Boom } = require("@hapi/boom");
const express = require("express");
const qrcodeTerminal = require("qrcode-terminal");
const qrcode = require("qrcode");
const pino = require("pino");

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// CORS
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});

let sock = null;
let botStatus = "disconnected";
let currentQrImage = null;

function queueMessage(jid, text, delay = 1500) {
  setTimeout(async () => {
    try {
      await sock.sendMessage(jid, { text });
    } catch (err) {
      console.error("Error sending message:", err.message);
    }
  }, delay + Math.random() * 1500);
}

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("auth_info_baileys");

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: "silent" }),
    browser: ["Facial Attendance Bot", "Chrome", "1.0.0"],
  });

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      botStatus = "qr_needed";
      qrcodeTerminal.generate(qr, { small: true });
      currentQrImage = await qrcode.toDataURL(qr);
      console.log("\n--- Scan QR Code with WhatsApp ---\n");
    }

    if (connection === "close") {
      const shouldReconnect =
        lastDisconnect?.error instanceof Boom
          ? lastDisconnect.error.output?.statusCode !==
            DisconnectReason.loggedOut
          : true;

      botStatus = shouldReconnect ? "disconnected" : "logged_out";
      console.log("Connection closed. Reconnecting:", shouldReconnect);

      if (shouldReconnect) {
        connectToWhatsApp();
      }
    } else if (connection === "open") {
      botStatus = "connected";
      currentQrImage = null;
      console.log("✅ WhatsApp connected successfully!");
    }
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("messages.upsert", async (m) => {
    if (m.type !== "notify") return;
    for (const msg of m.messages) {
      if (msg.key.fromMe) continue;
      const jid = msg.key.remoteJid;
      if (!jid || jid.endsWith("@g.us")) continue;

      const text =
        msg.message?.conversation || msg.message?.extendedTextMessage?.text || "";
      console.log(`Message from ${jid}: ${text}`);
    }
  });
}

app.get("/status", (req, res) => {
  res.json({ status: botStatus, qr: currentQrImage });
});

app.post("/send-message", async (req, res) => {
  if (botStatus !== "connected" || !sock) {
    return res.status(503).json({ error: "WhatsApp not connected" });
  }

  const { phone, message } = req.body;
  if (!phone || !message) {
    return res.status(400).json({ error: "phone and message are required" });
  }

  const jid = phone.includes("@") ? phone : `${phone}@s.whatsapp.net`;

  try {
    await sock.sendMessage(jid, { text: message });
    res.json({ success: true, message: "Message sent" });
  } catch (err) {
    console.error("Send message error:", err.message);
    res.status(500).json({ error: "Failed to send message" });
  }
});

app.post("/send-bulk", async (req, res) => {
  if (botStatus !== "connected" || !sock) {
    return res.status(503).json({ error: "WhatsApp not connected" });
  }

  const { messages } = req.body;
  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: "messages array is required" });
  }

  const results = [];
  for (const { phone, message } of messages) {
    const jid = phone.includes("@") ? phone : `${phone}@s.whatsapp.net`;
    try {
      await sock.sendMessage(jid, { text: message });
      results.push({ phone, success: true });
    } catch (err) {
      results.push({ phone, success: false, error: err.message });
    }
    await new Promise((r) => setTimeout(r, 2000 + Math.random() * 1000));
  }

  res.json({ results });
});

app.get("/qr", async (req, res) => {
  if (currentQrImage) {
    res.json({ qr: currentQrImage });
  } else {
    res.json({ qr: null, status: botStatus });
  }
});

connectToWhatsApp();

app.listen(PORT, () => {
  console.log(`WhatsApp service running on port ${PORT}`);
  console.log("Waiting for QR code scan...");
});

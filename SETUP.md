# 🐡 Puffer Community Bot V4 — Full Setup Guide

## What this bot does

| Feature | How |
|---|---|
| Live crypto news every 25 min | RSS feeds (CoinTelegraph, CoinDesk, Decrypt) |
| Live market prices | CoinGecko free API |
| Trending memecoins | DexScreener free API |
| Fear & Greed Index | Alternative.me free API |
| AI rewrites every post | Gemini API (your key) |
| AI-generated images | Pollinations.ai (free, no key) |
| Crypto GIFs on memes | Giphy public library |
| No repeated posts | Local history file tracks everything |
| Human-feeling delays | Random 3–18 second pauses before posting |
| Welcome new members | Auto-detects, Gemini writes personal welcome |
| Escalation guard | Auto-redirects listing/partnership questions |
| Coin launch teasing | Built-in daily hype post |
| Polls, debates, challenges | Scheduled throughout the day |

---

## Files

```
puffer_v2/
├── bot.py              ← Everything in one file
├── requirements.txt    ← Python packages
├── .env.example        ← Copy to .env
└── SETUP.md            ← This file
```

---

## Step 1 — Get your Telegram Bot Token

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Pick a name: `Puffer Community Bot`
4. Pick a username: `puffer_community_bot`
5. Copy the token — looks like `7123456789:ABCdef...`

---

## Step 2 — Get your Channel Chat ID

1. Add your bot as **Admin** in your channel
   - Channel Settings → Administrators → Add
   - Give it: Post Messages, Edit Messages, Delete Messages
2. Send any message in your channel
3. Open this URL in your browser (replace YOUR_TOKEN):
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
4. Find `"chat":{"id": -1001234567890}` — that number is your Chat ID

---

## Step 3 — Get your Gemini API Key

1. Go to: `https://aistudio.google.com`
2. Sign in with your Google account
3. Click **Get API Key** → **Create API Key**
4. Copy it — looks like `AIzaSy...`

Free tier gives you 15 requests/minute — more than enough.

---

## Step 4 — Set up your .env file

```bash
cp .env.example .env
nano .env   # or open in any text editor
```

Fill in your 3 values:
```
TELEGRAM_BOT_TOKEN=7123456789:ABCdef...
TELEGRAM_CHAT_ID=-1001234567890
GEMINI_API_KEY=AIzaSy...
```

---

## Step 5 — Install and run

```bash
# Install packages
pip install -r requirements.txt

# Load your .env and start
export $(cat .env | xargs)
python bot.py
```

You should see:
```
✅ Full schedule loaded — 30 jobs
🐡 Puffer Bot V4 starting…
```

---

## Step 6 — Run 24/7 (choose one)

### Option A — Railway.app (easiest, free)
1. Push this folder to a GitHub repo
2. Go to `railway.app` → New Project → Deploy from GitHub
3. Add your 3 environment variables in Settings → Variables
4. Deploy — done. Runs forever.

### Option B — Linux VPS (DigitalOcean, Hetzner, etc.)

Create a service file:
```bash
sudo nano /etc/systemd/system/puffer_bot.service
```

Paste this (update the paths):
```ini
[Unit]
Description=Puffer Community Bot V4
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/puffer_v2
EnvironmentFile=/home/ubuntu/puffer_v2/.env
ExecStart=/usr/bin/python3 /home/ubuntu/puffer_v2/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable puffer_bot
sudo systemctl start puffer_bot
sudo systemctl status puffer_bot
```

### Option C — Screen (quick test)
```bash
screen -S puffer
export $(cat .env | xargs)
python bot.py
# Ctrl+A then D to detach — bot keeps running
```

---

## Daily Post Schedule

| Time  | Post Type |
|-------|-----------|
| 06:00 | 🌅 GM post with AI image |
| 07:00 | 📊 Live market prices |
| 07:30 | 🔥 DexScreener trending |
| 08:00 | 📰 Live crypto news |
| 08:30 | 😂 Meme + GIF |
| 09:00 | 📊 Poll |
| 10:00 | 📚 Educational post |
| 10:30 | 📰 News |
| 11:00 | 🌐 Web3 insight |
| 11:30 | 🎁 Airdrop tip |
| 12:00 | 📊 Market update |
| 12:30 | 🐦 Funny Twitter moment |
| 13:00 | 🔥 Debate topic |
| 13:30 | 📰 News |
| 14:00 | 🔥 DexScreener update |
| 14:30 | 💪 Motivational |
| 15:00 | 😂 Meme + GIF |
| 15:30 | 🎯 Community challenge |
| 16:00 | 👀 Coin launch tease |
| 16:30 | 📰 News |
| 17:00 | 📚 Education |
| 17:30 | 📊 Poll |
| 18:00 | 🐦 Twitter moment |
| 18:30 | 🎁 Airdrop |
| 19:00 | 📊 Market update |
| 19:30 | 📰 News |
| 20:00 | 💪 Motivational + image |
| 20:30 | 😂 Meme |
| 21:00 | 📊 Market recap |
| 21:30 | 🏆 Community shoutout |
| 22:00 | 🔥 DexScreener |
| Every 25 min | 📰 News burst |
| Every 45 min | 🔥 Trending burst |

---

## Bot Commands (type in channel)

| Command | Does |
|---------|------|
| `/start` | Bot intro |
| `/news` | Posts fresh news now |
| `/trending` | Posts trending coins now |
| `/airdrop` | Posts airdrop tip now |
| `/meme` | Posts a meme now |

---

## How the bot feels human

- **Random delays** — waits 3 to 18 seconds before posting
- **Only replies 15% of the time** — doesn't dominate conversations
- **Escalation guard** — never answers listing/partnership questions
- **Gemini rewrites everything** — no two posts sound the same
- **No repeats** — tracks everything posted in `posted_history.json`
- **Welcomes members personally** — Gemini writes a custom welcome using their name

---

## Troubleshooting

**Bot not posting:**
- Check your TELEGRAM_CHAT_ID starts with `-100`
- Make sure bot is admin in the channel
- Check logs: `sudo journalctl -u puffer_bot -f`

**Gemini errors:**
- Verify your API key at `aistudio.google.com`
- Bot falls back to default text if Gemini fails — won't crash

**Images not showing:**
- Pollinations.ai can be slow sometimes — bot falls back to text-only

**Rate limited by Telegram:**
- Reduce posting frequency by removing some jobs from `schedule_all()`

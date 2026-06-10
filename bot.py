"""
PUFFER COMMUNITY BOT V4 — Full Upgrade
Live news • DexScreener • Gemini AI • Image generation • Human behaviour
"""

import os
import asyncio
import random
import logging
import json
import hashlib
from datetime import datetime, time as dtime
from pathlib import Path

import httpx
import google.generativeai as genai
from telegram import Bot, Update, InputMediaPhoto
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    filters, ContextTypes
)

# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── ENV ───────────────────────────────────────────────────────────────────────
BOT_TOKEN         = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID           = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
CRYPTOPANIC_KEY   = os.environ.get("CRYPTOPANIC_API_KEY", "")   # optional

if not BOT_TOKEN or not CHAT_ID:
    raise EnvironmentError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

# ── GEMINI SETUP ─────────────────────────────────────────────────────────────
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini = None
    log.warning("No GEMINI_API_KEY — AI rewriting disabled")

# ── POSTED HISTORY (no repeats) ───────────────────────────────────────────────
HISTORY_FILE = Path("posted_history.json")

def load_history() -> set:
    if HISTORY_FILE.exists():
        return set(json.loads(HISTORY_FILE.read_text()))
    return set()

def save_history(h: set):
    HISTORY_FILE.write_text(json.dumps(list(h)[-500:]))  # keep last 500

posted = load_history()

def already_posted(text: str) -> bool:
    key = hashlib.md5(text[:120].encode()).hexdigest()
    if key in posted:
        return True
    posted.add(key)
    save_history(posted)
    return False

# ── SUBSCRIPTION TEST ─────────────────────────────────────────────────────────
def passes_test(text: str) -> bool:
    blocked = ["buy puffer now", "puffer to the moon", "puffer holders only"]
    t = text.lower()
    return not any(b in t for b in blocked)

# ── HUMAN TIMING (feels natural, not robotic) ────────────────────────────────
async def human_delay():
    """Random 3–18 second delay before posting — feels human"""
    await asyncio.sleep(random.uniform(3, 18))

# ── SEND ──────────────────────────────────────────────────────────────────────
async def send(bot: Bot, text: str, image_url: str = None):
    if not passes_test(text):
        return
    if already_posted(text):
        log.info("Skipped duplicate post")
        return
    await human_delay()
    try:
        if image_url:
            try:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=image_url,
                    caption=text,
                    parse_mode="HTML"
                )
                return
            except Exception:
                pass  # fall through to text-only
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        log.info("✅ Posted: %s...", text[:60])
    except Exception as e:
        log.error("Send error: %s", e)

async def send_poll(bot: Bot, question: str, options: list):
    await human_delay()
    try:
        await bot.send_poll(
            chat_id=CHAT_ID,
            question=question,
            options=options,
            is_anonymous=False
        )
    except Exception as e:
        log.error("Poll error: %s", e)

# ── GEMINI AI REWRITER ────────────────────────────────────────────────────────
async def gemini_rewrite(raw: str, post_type: str = "news") -> str:
    """Use Gemini to rewrite raw data into engaging community post"""
    if not gemini:
        return raw

    prompts = {
        "news": f"""You are a crypto community manager for a memecoin Telegram channel called Puffer.
Rewrite this news into an engaging Telegram post. 
Rules:
- Max 200 words
- Use emojis naturally (not every line)
- End with ONE question to spark discussion
- Sound like a real human, not a bot
- Use HTML formatting: <b>bold</b> for key points
- Never mention Puffer price or tell people to buy
- Make it interesting even for someone who never heard of our coin

News: {raw}

Write only the post, nothing else.""",

        "dex": f"""You are a crypto community manager. 
Turn this DexScreener market data into a short exciting community update.
Rules:
- Max 150 words  
- Sound human and excited but not spammy
- End with a question
- Use emojis, HTML bold for coin names and numbers
- Don't tell people to buy anything

Data: {raw}

Write only the post.""",

        "meme": f"""You are a funny crypto community manager.
Write a hilarious relatable crypto meme post based on this topic: {raw}
Rules:
- Max 100 words
- Funny, relatable, self-aware humor
- End with 'Tag someone who does this 👇' or similar
- Use emojis
- HTML bold for punchline

Write only the post.""",

        "motivational": f"""You are an inspiring crypto community leader.
Write a short motivational post for a memecoin community about: {raw}
Rules:
- Max 120 words
- Real, genuine — not cheesy
- Relate to crypto journey struggles
- End with an engaging question
- Use emojis sparingly

Write only the post."""
    }

    try:
        prompt = prompts.get(post_type, prompts["news"])
        response = await asyncio.to_thread(gemini.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        log.error("Gemini error: %s", e)
        return raw

# ── LIVE DATA FETCHERS ────────────────────────────────────────────────────────

async def fetch_dexscreener_trending() -> list:
    """Fetch trending tokens from DexScreener"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.dexscreener.com/token-profiles/latest/v1",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = r.json()
            return data[:5] if isinstance(data, list) else []
    except Exception as e:
        log.error("DexScreener error: %s", e)
        return []

async def fetch_dexscreener_gainers() -> list:
    """Fetch top movers"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.dexscreener.com/token-boosts/top/v1",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = r.json()
            return data[:5] if isinstance(data, list) else []
    except Exception as e:
        log.error("DexScreener gainers error: %s", e)
        return []

async def fetch_coingecko_trending() -> list:
    """Fetch trending coins from CoinGecko"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/search/trending",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = r.json()
            return data.get("coins", [])[:7]
    except Exception as e:
        log.error("CoinGecko error: %s", e)
        return []

async def fetch_coingecko_market() -> dict:
    """Fetch BTC/ETH global market data"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": "bitcoin,ethereum,solana",
                    "order": "market_cap_desc"
                },
                headers={"User-Agent": "Mozilla/5.0"}
            )
            return {c["id"]: c for c in r.json()}
    except Exception as e:
        log.error("CoinGecko market error: %s", e)
        return {}

async def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed Index"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.alternative.me/fng/?limit=1")
            data = r.json()
            return data["data"][0]
    except Exception as e:
        log.error("Fear/Greed error: %s", e)
        return {}

async def fetch_crypto_news() -> list:
    """Fetch crypto news from RSS feeds"""
    feeds = [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
    ]
    items = []
    try:
        import xml.etree.ElementTree as ET
        async with httpx.AsyncClient(timeout=10) as client:
            feed_url = random.choice(feeds)
            r = await client.get(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.text)
            for item in root.iter("item"):
                title = item.find("title")
                desc  = item.find("description")
                link  = item.find("link")
                if title is not None:
                    items.append({
                        "title": title.text or "",
                        "description": (desc.text or "")[:200] if desc is not None else "",
                        "link": link.text or "" if link is not None else ""
                    })
                if len(items) >= 8:
                    break
    except Exception as e:
        log.error("RSS error: %s", e)
    return items

async def fetch_cryptopanic_news() -> list:
    """Fetch from CryptoPanic if key available"""
    if not CRYPTOPANIC_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://cryptopanic.com/api/v1/posts/",
                params={
                    "auth_token": CRYPTOPANIC_KEY,
                    "filter": "hot",
                    "kind": "news"
                }
            )
            return r.json().get("results", [])[:5]
    except Exception as e:
        log.error("CryptoPanic error: %s", e)
        return []

async def fetch_meme_gif() -> str:
    """Fetch a crypto/memecoin related gif URL"""
    # Curated list of crypto/memecoin related public gif URLs
    gifs = [
        "https://media.giphy.com/media/JtWqekjMCCKKSRQYQY/giphy.gif",  # crypto moon
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",  # doge
        "https://media.giphy.com/media/26BRuo6sLetdllPAQ/giphy.gif",  # stonks
        "https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif",  # money rain
        "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",  # rocket
        "https://media.giphy.com/media/l3q2wJsC23ikJg9xe/giphy.gif",  # pepe vibes
        "https://media.giphy.com/media/Qy2E4KFpvPSNa/giphy.gif",      # doge wow
        "https://media.giphy.com/media/13HgwGsXF0aiGY/giphy.gif",     # bull run
    ]
    return random.choice(gifs)

# ── IMAGE GENERATION VIA GEMINI ───────────────────────────────────────────────
async def generate_image_prompt(topic: str) -> str:
    """Ask Gemini to create an image prompt, then use a free image service"""
    # We use Pollinations.ai — completely free, no API key
    # It generates images from text prompts
    prompts = {
        "market": f"crypto memecoin market chart moon rocket bulls bears colorful digital art",
        "meme": f"funny crypto frog pepe doge meme digital art vibrant colors",
        "airdrop": f"crypto airdrop free tokens raining coins digital art colorful",
        "education": f"blockchain web3 technology education digital art futuristic",
        "gm": f"good morning crypto sunrise rocket moon colorful digital art",
        "trending": f"trending memecoin chart going up rocket moon digital neon art",
    }
    prompt = prompts.get(topic, f"crypto memecoin {topic} digital art colorful")
    encoded = prompt.replace(" ", "%20")
    seed = random.randint(1, 9999)
    return f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=400&nologo=true"

# ── POST JOBS ─────────────────────────────────────────────────────────────────

async def post_gm(context: ContextTypes.DEFAULT_TYPE):
    img = await generate_image_prompt("gm")
    messages = [
        "Rise up fam! 🌅 Another day, another opportunity in Web3.\n\nThe market doesn't care about yesterday. Only what you do today. 💪\n\n<b>GM! What's your focus today?</b> 👇",
        "☀️ <b>GM Crypto family!</b>\n\nWhile most people are still sleeping, we're already thinking about the next move.\n\nThat's the difference. 🧠\n\n<b>Drop a 🐡 if you're ready to make moves today!</b>",
        "🌅 <b>Good Morning from the Puffer fam!</b>\n\nEvery expert was once a beginner.\nEvery whale was once broke.\nEvery winner was once a doubter.\n\nKeep building. 💎\n\n<b>What are you working on in Web3 right now?</b> 👇",
    ]
    text = await gemini_rewrite(random.choice(messages), "motivational")
    await send(context.bot, text, img)

async def post_market_update(context: ContextTypes.DEFAULT_TYPE):
    market = await fetch_coingecko_market()
    fg = await fetch_fear_greed()

    if market:
        btc = market.get("bitcoin", {})
        eth = market.get("ethereum", {})
        sol = market.get("solana", {})

        btc_price = btc.get("current_price", 0)
        btc_change = btc.get("price_change_percentage_24h", 0)
        eth_price = eth.get("current_price", 0)
        eth_change = eth.get("price_change_percentage_24h", 0)
        sol_price = sol.get("current_price", 0)
        sol_change = sol.get("price_change_percentage_24h", 0)

        fg_value = fg.get("value", "?")
        fg_class  = fg.get("value_classification", "Unknown")

        btc_emoji = "📈" if btc_change > 0 else "📉"
        eth_emoji = "📈" if eth_change > 0 else "📉"
        sol_emoji = "📈" if sol_change > 0 else "📉"

        raw = f"""
BTC: ${btc_price:,.0f} {btc_emoji} {btc_change:+.1f}%
ETH: ${eth_price:,.0f} {eth_emoji} {eth_change:+.1f}%
SOL: ${sol_price:,.0f} {sol_emoji} {sol_change:+.1f}%
Fear & Greed: {fg_value}/100 — {fg_class}
        """.strip()

        text = await gemini_rewrite(raw, "dex")
    else:
        text = "📊 <b>Market Update</b>\n\nMarkets moving — stay alert and manage your risk.\n\n<b>How's your portfolio looking today?</b> 👇"

    img = await generate_image_prompt("market")
    await send(context.bot, text, img)

async def post_dex_trending(context: ContextTypes.DEFAULT_TYPE):
    tokens = await fetch_dexscreener_trending()

    if tokens:
        lines = []
        for t in tokens[:4]:
            name = t.get("description", t.get("tokenAddress", "Unknown"))[:30]
            chain = t.get("chainId", "")
            lines.append(f"• <b>{name}</b> [{chain}]")

        raw = "🔥 Trending on DexScreener right now:\n" + "\n".join(lines)
        text = await gemini_rewrite(raw, "dex")
    else:
        trending = await fetch_coingecko_trending()
        if trending:
            lines = [f"• <b>{c['item']['name']}</b> (#{c['item']['market_cap_rank'] or '?'})" for c in trending[:5]]
            raw = "🔥 Trending on CoinGecko:\n" + "\n".join(lines)
            text = await gemini_rewrite(raw, "dex")
        else:
            text = "🔥 <b>Trending Watch</b>\n\nMemecoins are moving fast today — keep your eyes on low cap gems with volume spikes.\n\n<b>What gem are you watching right now?</b> 👇"

    img = await generate_image_prompt("trending")
    await send(context.bot, text, img)

async def post_news(context: ContextTypes.DEFAULT_TYPE):
    # Try CryptoPanic first, then RSS
    items = await fetch_cryptopanic_news()
    if not items:
        items = await fetch_crypto_news()

    if items:
        item = random.choice(items)
        if isinstance(item, dict):
            title = item.get("title", item.get("title", ""))
            desc  = item.get("description", item.get("url", ""))
            raw   = f"{title}. {desc}"
        else:
            raw = str(item)

        if raw.strip():
            text = await gemini_rewrite(raw, "news")
        else:
            text = "📰 <b>Crypto markets are moving</b> — big things happening across Web3 today.\n\n<b>What news caught your eye today?</b> 👇"
    else:
        text = "📡 <b>Market Intel</b>\n\nThe crypto space never sleeps. Something is always happening.\n\n<b>What's the biggest crypto story you've seen today? Drop it below 👇</b>"

    await send(context.bot, text)

async def post_meme(context: ContextTypes.DEFAULT_TYPE):
    topics = [
        "buying the dip every single time it dips",
        "explaining crypto to your family at dinner",
        "checking your portfolio every 5 minutes",
        "selling right before the pump",
        "being called crazy for believing in crypto",
        "portfolio going down after you tell your friend to buy",
        "staying up until 3am watching charts",
        "when a memecoin you ape into actually moons",
        "diamond hands during a 70% crash",
        "when someone asks if crypto is a scam",
    ]
    topic = random.choice(topics)
    text = await gemini_rewrite(topic, "meme")
    gif = await fetch_meme_gif()
    await send(context.bot, text, gif)

async def post_poll(context: ContextTypes.DEFAULT_TYPE):
    polls = [
        {"q": "What's your biggest crypto regret?", "o": ["Selling too early 😭", "Buying too late", "Not DCA-ing", "Trusting the wrong project"]},
        {"q": "What best describes you right now?", "o": ["Diamond hands 💎", "Taking profits", "Buying the dip", "Just watching 👀"]},
        {"q": "Which sector excites you most?", "o": ["Memecoins 🐸", "DeFi 💰", "AI + Crypto 🤖", "GameFi 🎮"]},
        {"q": "How long have you been in crypto?", "o": ["Under 1 year 🐣", "1–3 years", "3–5 years", "5+ years OG 👑"]},
        {"q": "What would you do if your bag 10x'd tomorrow?", "o": ["Sell everything 💸", "Hold it all 💎", "Take 50% profit", "Buy more 😂"]},
        {"q": "What's your #1 rule in crypto?", "o": ["Never invest what you can't lose", "Always take profits", "DYOR always", "Trust the community"]},
        {"q": "Bull or bear right now?", "o": ["Full bull 🐂🔥", "Cautiously bullish", "Neutral, watching", "Bearish for now 🐻"]},
    ]
    p = random.choice(polls)
    await send_poll(context.bot, p["q"], p["o"])

async def post_airdrop(context: ContextTypes.DEFAULT_TYPE):
    posts = [
        "Airdrop farming tip — many projects track wallet age, number of transactions, and unique protocols used. A fresh wallet with 2 interactions won't qualify for most serious drops. Keep building your on-chain history now.",
        "Real airdrop red flags to know: any drop asking you to send ETH/BNB first, seed phrase required to claim, no official announcement link, rushed 24-hour deadline, DMs only. Legitimate projects never need your funds to give you funds.",
        "Testnet farming is still one of the best free opportunities in Web3. You're doing real testing for the protocol, building on-chain history, and positioning for a potential mainnet launch drop — all for the cost of gas on test networks (which is free).",
        "The Arbitrum airdrop gave some wallets $10,000+. The Uniswap airdrop gave $1,200 to anyone who ever traded. ENS gave thousands to domain holders. All of these rewarded consistent, early users — not bots.",
        "Airdrop consistency tip: It's better to interact with 3 protocols every week for 6 months than to do 100 transactions in one day. Projects can detect wash activity. Real usage wins.",
    ]
    raw = random.choice(posts)
    text = await gemini_rewrite(raw, "news")
    img = await generate_image_prompt("airdrop")
    await send(context.bot, text, img)

async def post_educational(context: ContextTypes.DEFAULT_TYPE):
    topics = [
        "What is a liquidity pool and how does it work in DeFi? Explain impermanent loss simply.",
        "What is the difference between Layer 1 and Layer 2 blockchains? Why does it matter for gas fees?",
        "What is a smart contract and why does it make blockchain powerful? Give a simple real example.",
        "What is DePIN — Decentralized Physical Infrastructure — and why is it one of the most interesting sectors in Web3?",
        "What is on-chain activity and why do airdrops care about it? How to build genuine on-chain history.",
        "What is wallet security 101 — seed phrases, hardware wallets, contract approvals, and the most common mistakes people make.",
        "What is tokenomics and why does it matter more than hype? How to read a project's token supply, vesting, and distribution.",
        "What is DeFi yield farming — how does it work, what are the real risks, and how to stay safe?",
    ]
    topic = random.choice(topics)
    prompt = f"Write a beginner-friendly educational Telegram post about: {topic}. Max 200 words. Use simple language, emojis, HTML bold for key terms. End with a question."
    if gemini:
        try:
            response = await asyncio.to_thread(gemini.generate_content, prompt)
            text = response.text.strip()
        except Exception:
            text = f"📚 <b>Web3 Education</b>\n\n{topic}\n\n<b>What questions do you have about this?</b> 👇"
    else:
        text = f"📚 <b>Web3 Education</b>\n\n{topic}\n\n<b>What questions do you have about this?</b> 👇"

    img = await generate_image_prompt("education")
    await send(context.bot, text, img)

async def post_debate(context: ContextTypes.DEFAULT_TYPE):
    topics = [
        "Memecoins will outlast most 'serious' utility tokens. Community IS the utility.",
        "The next bull run will be AI + Crypto driven, not memecoins.",
        "Most people don't actually need a hardware wallet — better habits matter more.",
        "Crypto Twitter does more harm than good to the market.",
        "The best altcoins haven't been created yet — we're still incredibly early.",
        "DeFi will eventually replace traditional banks for most everyday people.",
        "Anonymous founders are a red flag no matter how good the project looks.",
        "NFTs are not dead — they just needed to find real utility beyond profile pictures.",
    ]
    topic = random.choice(topics)
    text = await gemini_rewrite(f"Hot take debate: {topic}", "meme")
    await send(context.bot, text)

async def post_motivational(context: ContextTypes.DEFAULT_TYPE):
    topics = [
        "Most people quit right before their breakthrough. Staying consistent during hard times.",
        "Every crypto expert you follow got wrecked at least once. Losing is part of the journey.",
        "You came to Web3 before most people even know it exists. What that means for your future.",
        "The bear market is where real builders separate from tourists.",
        "Your biggest crypto mistake is not the end — it's the education that changes everything.",
        "Believe in yourself even when the market is red and everyone is negative.",
    ]
    topic = random.choice(topics)
    text = await gemini_rewrite(topic, "motivational")
    img = await generate_image_prompt("gm")
    await send(context.bot, text, img)

async def post_twitter_moment(context: ContextTypes.DEFAULT_TYPE):
    stories = [
        "Someone on X today: 'I'm never buying crypto again' — same person 48 hours later: 'just deployed my savings into a new memecoin, here's my thesis thread 🧵'",
        "Crypto Twitter moment: Guy calls Bitcoin a scam in 2017. Calls it a scam in 2019. Calls it a scam in 2021. Now he's a 'crypto educator' on YouTube.",
        "Real thing happening on X right now: Person posts their portfolio is down 60%. Replies are a mix of: 'HODL!' and 'this is why I don't touch crypto' and 'buy more obviously'",
        "X.com behavior: Someone posts a 47-tweet thread explaining why a certain coin will go to zero. That coin pumps 200% the next day. Thread is still up.",
        "The funniest thing on Crypto Twitter: People who sold Bitcoin at $10k posting 'I knew all along' when it hits a new ATH 😂",
        "Classic X moment: 'I just put all my savings in crypto, this is my financial freedom journey' — posted Monday. 'Markets are manipulated' — posted Tuesday.",
    ]
    raw = random.choice(stories)
    text = await gemini_rewrite(raw, "meme")
    gif = await fetch_meme_gif()
    await send(context.bot, text, gif)

async def post_web3_insight(context: ContextTypes.DEFAULT_TYPE):
    insights = [
        "Web3 careers that don't require coding: community management, crypto content creation, DAO coordination, tokenomics research, growth marketing, project management. The ecosystem needs all skills.",
        "The difference between a good and great crypto community: great communities make members feel noticed, valued, and like they belong to something bigger than a price chart.",
        "Why on-chain activity matters beyond airdrops: your wallet history is becoming your Web3 reputation. Future lending, access, and opportunities may be tied to it.",
        "AI in crypto isn't just hype. Projects are using AI for trading, security audits, fraud detection, and content. The intersection is one of the most exciting spaces to watch.",
        "DePIN explained simply: instead of Amazon building server farms, regular people run nodes and earn crypto. Instead of Uber owning cars, you share your WiFi or drive and earn. Real world utility, decentralized.",
    ]
    raw = random.choice(insights)
    text = await gemini_rewrite(raw, "news")
    img = await generate_image_prompt("education")
    await send(context.bot, text, img)

async def post_coin_launch_tease(context: ContextTypes.DEFAULT_TYPE):
    """Tease upcoming coin launch — human, exciting, no financial advice"""
    prompt = """Write a short exciting Telegram post hinting at an upcoming memecoin launch for the Puffer community.
Rules:
- Sound like an excited community member, not a marketer
- Don't promise returns or tell people to buy
- Build curiosity and excitement
- Max 120 words
- End with a question like 'Are you ready?' or 'Who's watching this space?'
- Use emojis and HTML bold
- Mention 'something big is coming' style language"""

    if gemini:
        try:
            response = await asyncio.to_thread(gemini.generate_content, prompt)
            text = response.text.strip()
        except Exception:
            text = "👀 <b>Something is brewing in the Puffer ecosystem...</b>\n\nWe can't say too much just yet. But the team has been building.\n\nStay close. Stay ready. 🐡\n\n<b>Are you watching this space?</b> 👇"
    else:
        text = "👀 <b>Something is brewing in the Puffer ecosystem...</b>\n\nWe can't say too much just yet. But the team has been building.\n\nStay close. Stay ready. 🐡\n\n<b>Are you watching this space?</b> 👇"

    img = await generate_image_prompt("trending")
    await send(context.bot, text, img)

async def post_market_recap(context: ContextTypes.DEFAULT_TYPE):
    market = await fetch_coingecko_market()
    fg = await fetch_fear_greed()

    if market:
        btc = market.get("bitcoin", {})
        change = btc.get("price_change_percentage_24h", 0)
        price = btc.get("current_price", 0)
        fg_val = fg.get("value", "?")
        fg_cls = fg.get("value_classification", "")
        emoji = "📈" if change > 0 else "📉"

        raw = f"End of day recap: BTC at ${price:,.0f} {emoji} {change:+.1f}% today. Market sentiment: {fg_val}/100 {fg_cls}. Overall: {'positive session' if change > 0 else 'tough day but we keep building'}."
        text = await gemini_rewrite(raw, "dex")
    else:
        text = "🌙 <b>Daily Recap</b>\n\nAnother day in crypto done. Red or green — we keep building.\n\nPatience + consistency = the winning formula. 💎\n\n<b>How did today treat your portfolio?</b> 👇"

    await send(context.bot, text)

async def post_community_challenge(context: ContextTypes.DEFAULT_TYPE):
    challenges = [
        ("🎯 <b>Community Challenge!</b>\n\nShare <b>one thing you learned about crypto this week</b>.\n\nBest insight gets a shoutout! Drop your knowledge below 👇", None),
        ("🏆 <b>Prediction Time!</b>\n\nWill BTC be higher or lower this time next week?\n\nDrop: 📈 for higher | 📉 for lower\n\nWe'll check back together! 👇", None),
        ("💬 <b>Intro Challenge!</b>\n\nIf you've never introduced yourself here — today is the day!\n\nTell us:\n🌍 Where you're from\n💎 Your favorite coin\n📚 Your biggest crypto lesson so far\n\n<b>Go! 👇</b>", None),
        ("🔥 <b>Hot Take Challenge!</b>\n\nGive us your most controversial crypto opinion.\n\nMost liked comment gets community MVP for the day! 🏅\n\n<b>Don't hold back 👇</b>", None),
    ]
    text, img = random.choice(challenges)
    await send(context.bot, text, img)

async def post_shoutout(context: ContextTypes.DEFAULT_TYPE):
    posts = [
        "🏆 <b>Community Appreciation</b>\n\nTo everyone asking questions, sharing insights, helping newcomers, and showing up daily — you are what makes this community real.\n\n🙌 This isn't just a channel. It's a movement.\n\n<b>Shoutout someone who helped you in crypto!</b> 👇",
        "⭐ <b>Real Talk</b>\n\nThe strongest communities aren't built by founders.\nThey're built by members who keep showing up.\n\nThank you for being here. 💎\n\n<b>What do you love most about this community?</b> 👇",
        "🎖️ <b>Member Spotlight</b>\n\nIf you've been lurking — today is a great day to say hello.\n\nThis community is only as strong as the people in it.\n\n<b>Where are you joining from? Drop your flag! 👇</b>",
    ]
    await send(context.bot, random.choice(posts))

# ── NEW MEMBER WELCOME ────────────────────────────────────────────────────────
async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "friend"
        prompt = f"""Write a warm, genuine welcome message for a new Telegram crypto community member named {name}.
Rules:
- Sound like a friendly real human, not a bot
- Max 100 words
- Ask where they're from, their favorite memecoin, and their biggest crypto lesson
- Use emojis naturally
- HTML bold for key phrases
- Mention the community is about learning and growing together"""

        if gemini:
            try:
                response = await asyncio.to_thread(gemini.generate_content, prompt)
                text = response.text.strip()
            except Exception:
                text = f"👋 <b>Welcome {name}!</b>\n\nSo glad you're here 🐡\n\nQuick intro:\n🌍 Where are you from?\n💎 Favorite memecoin?\n📚 Biggest crypto lesson so far?\n\nThis community is about learning, laughing, and growing together. Jump right in! 🚀"
        else:
            text = f"👋 <b>Welcome {name}!</b>\n\nSo glad you're here 🐡\n\nQuick intro:\n🌍 Where are you from?\n💎 Favorite memecoin?\n📚 Biggest crypto lesson so far?\n\nThis community is about learning, laughing, and growing together. Jump right in! 🚀"

        await send(context.bot, text)

# ── MESSAGE HANDLER (human participation) ────────────────────────────────────
ESCALATION_KEYWORDS = [
    "listing", "partnership", "treasury", "roadmap",
    "team decision", "token launch", "when cex", "when binance",
    "when launch", "when listed", "contract address"
]

CASUAL_REPLIES = [
    "💯 This is exactly the energy we need in here.",
    "🔥 Real talk. The community is what makes or breaks any project.",
    "🧠 Solid take. Anyone else have thoughts on this?",
    "💎 That's the mindset right there.",
    "📈 Interesting — the market will show us who's right!",
    "🌍 Love seeing perspectives from across the globe in here.",
    "💡 That's worth saving. Good insight.",
    "🚀 This is why this community is different.",
    "😂 Someone tag this for the weekly recap.",
    "👀 Now THAT is a take. Thoughts fam?",
]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()

    # Escalation guard
    if any(kw in text for kw in ESCALATION_KEYWORDS):
        if random.random() < 0.6:
            await asyncio.sleep(random.uniform(5, 20))
            await update.message.reply_text(
                "📌 The community leadership can provide the most accurate answer for that — best to check with them directly!",
                parse_mode="HTML"
            )
        return

    # Human participation: ~15% of messages, with natural delay
    if random.random() < 0.15:
        await asyncio.sleep(random.uniform(8, 45))  # feels human
        reply = random.choice(CASUAL_REPLIES)
        try:
            await update.message.reply_text(reply, parse_mode="HTML")
        except Exception as e:
            log.error("Reply error: %s", e)

# ── COMMANDS ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐡 <b>Puffer Community Bot V4 is live!</b>\n\nPosting live market data, real news, memes, education and more — 24/7.\n\nCommands: /news /trending /fact /airdrop /meme",
        parse_mode="HTML"
    )

async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_news(context)

async def cmd_trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_dex_trending(context)

async def cmd_airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_airdrop(context)

async def cmd_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_meme(context)

# ── SCHEDULE ──────────────────────────────────────────────────────────────────
def schedule_all(app: Application):
    jq = app.job_queue

    # Morning
    jq.run_daily(post_gm,               dtime(6, 0),  name="gm")
    jq.run_daily(post_market_update,    dtime(7, 0),  name="market_am")
    jq.run_daily(post_dex_trending,     dtime(7, 30), name="dex_am")
    jq.run_daily(post_news,             dtime(8, 0),  name="news_1")
    jq.run_daily(post_meme,             dtime(8, 30), name="meme_am")
    jq.run_daily(post_poll,             dtime(9, 0),  name="poll_am")

    # Midday
    jq.run_daily(post_educational,      dtime(10, 0), name="edu")
    jq.run_daily(post_news,             dtime(10, 30),name="news_2")
    jq.run_daily(post_web3_insight,     dtime(11, 0), name="web3")
    jq.run_daily(post_airdrop,          dtime(11, 30),name="airdrop")
    jq.run_daily(post_market_update,    dtime(12, 0), name="market_noon")
    jq.run_daily(post_twitter_moment,   dtime(12, 30),name="twitter")

    # Afternoon
    jq.run_daily(post_debate,           dtime(13, 0), name="debate")
    jq.run_daily(post_news,             dtime(13, 30),name="news_3")
    jq.run_daily(post_dex_trending,     dtime(14, 0), name="dex_pm")
    jq.run_daily(post_motivational,     dtime(14, 30),name="motivate_pm")
    jq.run_daily(post_meme,             dtime(15, 0), name="meme_pm")
    jq.run_daily(post_community_challenge, dtime(15, 30), name="challenge")
    jq.run_daily(post_coin_launch_tease,dtime(16, 0), name="launch_tease")
    jq.run_daily(post_news,             dtime(16, 30),name="news_4")

    # Evening
    jq.run_daily(post_educational,      dtime(17, 0), name="edu_pm")
    jq.run_daily(post_poll,             dtime(17, 30),name="poll_pm")
    jq.run_daily(post_twitter_moment,   dtime(18, 0), name="twitter_pm")
    jq.run_daily(post_airdrop,          dtime(18, 30),name="airdrop_pm")
    jq.run_daily(post_market_update,    dtime(19, 0), name="market_eve")
    jq.run_daily(post_news,             dtime(19, 30),name="news_5")

    # Night
    jq.run_daily(post_motivational,     dtime(20, 0), name="motivate_night")
    jq.run_daily(post_meme,             dtime(20, 30),name="meme_night")
    jq.run_daily(post_market_recap,     dtime(21, 0), name="recap")
    jq.run_daily(post_shoutout,         dtime(21, 30),name="shoutout")
    jq.run_daily(post_dex_trending,     dtime(22, 0), name="dex_night")

    # News burst every 25 minutes
    jq.run_repeating(post_news,         interval=1500, first=120, name="news_burst")

    # Market data every 45 minutes
    jq.run_repeating(post_dex_trending, interval=2700, first=300, name="dex_burst")

    log.info("✅ Full schedule loaded — %d jobs", len(jq.jobs()))

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("news",     cmd_news))
    app.add_handler(CommandHandler("trending", cmd_trending))
    app.add_handler(CommandHandler("airdrop",  cmd_airdrop))
    app.add_handler(CommandHandler("meme",     cmd_meme))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    schedule_all(app)

    log.info("🐡 Puffer Bot V4 starting…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

"""
General utility commands.

Free/no-key APIs used directly: TinyURL (/short), file.io (/filetolink),
Aladhan (/namaz), CoinGecko (/crypto). Key-gated: /webss, /stock, /news
(see .env.example) — they reply "not configured" until you add a key.
"""
import io
import secrets
import string

import requests
import qrcode
from PIL import Image

import config
import database as db
from locales.loader import t
from telegram import Update
from telegram.ext import ContextTypes


def _touch(update: Update):
    u = update.effective_user
    db.upsert_user(u.id, u.username, u.first_name)


# ---------- /dp ----------

async def dp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /dp @username")
        return

    username = context.args[0].lstrip("@")
    try:
        chat = await context.bot.get_chat(f"@{username}")
        photos = await context.bot.get_user_profile_photos(chat.id, limit=1)
        if not photos.photos:
            await update.message.reply_text("📭 No profile photo found (or it's private).")
            return
        file_id = photos.photos[0][-1].file_id
        await update.message.reply_photo(photo=file_id)
    except Exception:
        await update.message.reply_text(
            "❌ Couldn't fetch that profile photo. The bot can only see users "
            "who share a group with it or have a public username it has interacted with."
        )


# ---------- /short ----------

async def short_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /short <url>")
        return

    url = context.args[0]
    try:
        resp = requests.get(
            "https://tinyurl.com/api-create.php", params={"url": url}, timeout=15
        )
        if resp.status_code == 200 and resp.text.startswith("http"):
            await update.message.reply_text(f"🔗 {resp.text}")
        else:
            await update.message.reply_text(t("error_generic", lang))
    except requests.RequestException:
        await update.message.reply_text(t("error_generic", lang))


# ---------- /webss ----------

async def webss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /webss <url>")
        return

    if not config.SCREENSHOT_API_KEY:
        await update.message.reply_text(t("feature_not_configured", lang))
        return

    url = context.args[0]
    try:
        api_url = (
            "https://api.screenshotmachine.com"
            f"?key={config.SCREENSHOT_API_KEY}&url={url}&dimension=1024x768"
        )
        resp = requests.get(api_url, timeout=30)
        if resp.status_code == 200:
            await update.message.reply_photo(photo=io.BytesIO(resp.content))
        else:
            await update.message.reply_text(t("error_generic", lang))
    except requests.RequestException:
        await update.message.reply_text(t("error_generic", lang))


# ---------- /filetolink ----------

async def filetolink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Uses file.io (free, no key) instead of raw Telegram file URLs — a raw
    Telegram file URL embeds the bot token in the path, which would leak
    the bot's token to anyone the link is shared with. file.io gives a
    disposable link that auto-expires instead."""
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    reply = update.message.reply_to_message
    doc = reply.document if reply else None
    if not doc:
        await update.message.reply_text("↩️ Reply to a file with /filetolink")
        return

    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ File too large (Telegram bots can fetch max 20MB).")
        return

    try:
        file = await doc.get_file()
        file_bytes = await file.download_as_bytearray()
        resp = requests.post(
            "https://file.io/?expires=1d",
            files={"file": (doc.file_name or "file", bytes(file_bytes))},
            timeout=60,
        )
        data = resp.json()
        if data.get("success"):
            await update.message.reply_text(f"📎 Link (expires in 24h, single download):\n{data['link']}")
        else:
            await update.message.reply_text(t("error_generic", lang))
    except (requests.RequestException, ValueError):
        await update.message.reply_text(t("error_generic", lang))


# ---------- /qr ----------

async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    # QR READER: if replying to a photo, decode it instead of generating one
    reply = update.message.reply_to_message
    if reply and reply.photo:
        try:
            from pyzbar.pyzbar import decode as qr_decode
        except ImportError:
            await update.message.reply_text(t("feature_not_configured", lang))
            return
        try:
            file = await reply.photo[-1].get_file()
            photo_bytes = await file.download_as_bytearray()
            img = Image.open(io.BytesIO(bytes(photo_bytes)))
            results = qr_decode(img)
            if not results:
                await update.message.reply_text("📭 No QR code found in that image.")
                return
            texts = "\n".join(r.data.decode("utf-8", errors="replace") for r in results)
            await update.message.reply_text(f"🔍 {texts}")
        except Exception:
            await update.message.reply_text(t("error_generic", lang))
        return

    # QR GENERATOR
    if not context.args:
        await update.message.reply_text("Usage: /qr <text>   (or reply to a QR photo to decode it)")
        return

    text = " ".join(context.args)
    try:
        img = qrcode.make(text)
        buf = io.BytesIO()
        buf.name = "qr.png"
        img.save(buf)
        buf.seek(0)
        await update.message.reply_photo(photo=buf)
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


# ---------- /namaz ----------

async def namaz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    city = " ".join(context.args) if context.args else "Dhaka"

    try:
        resp = requests.get(
            "https://api.aladhan.com/v1/timingsByCity",
            params={"city": city, "country": "Bangladesh", "method": 1},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 200:
            await update.message.reply_text("❌ City not found.")
            return
        timings = data["data"]["timings"]
        lines = [f"🕌 {city} — নামাজের সময়" if lang == "bn" else f"🕌 Prayer times — {city}"]
        for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
            lines.append(f"• {name}: {timings.get(name, '?')}")
        await update.message.reply_text("\n".join(lines))
    except (requests.RequestException, KeyError, ValueError):
        await update.message.reply_text(t("error_generic", lang))


# ---------- /crypto ----------

_CRYPTO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "DOGE": "dogecoin", "XRP": "ripple", "ADA": "cardano",
}


async def crypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /crypto <symbol>  e.g. /crypto BTC")
        return

    symbol = context.args[0].upper()
    coin_id = _CRYPTO_IDS.get(symbol, symbol.lower())

    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=15,
        )
        data = resp.json()
        if coin_id not in data:
            await update.message.reply_text("❌ Unknown symbol/coin.")
            return
        price = data[coin_id]["usd"]
        change = data[coin_id].get("usd_24h_change", 0)
        arrow = "📈" if change >= 0 else "📉"
        await update.message.reply_text(f"{arrow} {symbol}: ${price:,.4f}  ({change:+.2f}% 24h)")
    except (requests.RequestException, KeyError, ValueError):
        await update.message.reply_text(t("error_generic", lang))


# ---------- /stock ----------

async def stock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /stock <symbol>  e.g. /stock AAPL")
        return

    if not config.ALPHAVANTAGE_API_KEY:
        await update.message.reply_text(t("feature_not_configured", lang))
        return

    symbol = context.args[0].upper()
    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": config.ALPHAVANTAGE_API_KEY,
            },
            timeout=15,
        )
        data = resp.json().get("Global Quote", {})
        price = data.get("05. price")
        change_pct = data.get("10. change percent")
        if not price:
            await update.message.reply_text("❌ Unknown symbol.")
            return
        await update.message.reply_text(f"📊 {symbol}: ${float(price):,.2f}  ({change_pct})")
    except (requests.RequestException, ValueError):
        await update.message.reply_text(t("error_generic", lang))


# ---------- /password ----------

async def password_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    length = 16
    if context.args and context.args[0].isdigit():
        length = max(6, min(64, int(context.args[0])))

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    pw = "".join(secrets.choice(alphabet) for _ in range(length))
    # sent as plain text (no Markdown) to avoid escaping issues with symbol characters
    await update.message.reply_text(f"🔐 {pw}")


# ---------- /checkpass ----------

async def checkpass_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    if not context.args:
        await update.message.reply_text("Usage: /checkpass <password>")
        return

    pw = " ".join(context.args)
    score = 0
    feedback = []

    if len(pw) >= 12:
        score += 2
    elif len(pw) >= 8:
        score += 1
    else:
        feedback.append("too short (use 12+ characters)")

    if any(c.islower() for c in pw):
        score += 1
    if any(c.isupper() for c in pw):
        score += 1
    else:
        feedback.append("add uppercase letters")
    if any(c.isdigit() for c in pw):
        score += 1
    else:
        feedback.append("add numbers")
    if any(c in string.punctuation for c in pw):
        score += 1
    else:
        feedback.append("add symbols")

    common = {"password", "123456", "qwerty", "letmein", "111111", "12345678"}
    if pw.lower() in common:
        score = 0
        feedback = ["this is one of the most common passwords in the world"]

    labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong", "Excellent"]
    label = labels[min(score, len(labels) - 1)]

    text = f"🔎 Strength: {label} ({score}/6)"
    if feedback:
        text += "\n💡 " + "; ".join(feedback)
    await update.message.reply_text(text)

    # delete the user's message containing the plaintext password, best-effort
    try:
        await update.message.delete()
    except Exception:
        pass


# ---------- /news ----------

async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    if not config.NEWSAPI_KEY:
        await update.message.reply_text(t("feature_not_configured", lang))
        return

    try:
        resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"country": "bd", "pageSize": 5, "apiKey": config.NEWSAPI_KEY},
            timeout=15,
        )
        data = resp.json()
        articles = data.get("articles", [])
        if not articles:
            await update.message.reply_text("📭 No headlines available right now.")
            return
        lines = ["📰 Bangladesh — Top Headlines"]
        for i, a in enumerate(articles[:5], 1):
            lines.append(f"{i}. {a.get('title', '?')}")
        await update.message.reply_text("\n".join(lines))
    except (requests.RequestException, ValueError):
        await update.message.reply_text(t("error_generic", lang))

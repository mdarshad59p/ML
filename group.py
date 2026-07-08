"""
Group-zone commands.

IMPORTANT HONEST LIMITATION — please read before relying on /deletelog:
The Telegram Bot API does NOT notify bots when a user deletes a message.
There is no "on_delete" event for regular bots — only client apps (or
MTProto "userbot" sessions, which need a full user account login and are
against Telegram's bot-usage norms to run persistently) can detect deletions
in real time. What this bot actually does is log the last ~500 messages it
sees per group (via the passive `log_all_messages` handler registered in
bot.py), and /deletelog shows that recent activity log — it is NOT a true
real-time "someone deleted this" alert. Please set expectations with your
users accordingly; don't market it as catching deletions live.

/lastseen is similarly best-effort: it only updates when the bot actually
sees a message from that user (in a chat it's part of), not true Telegram
"online/offline" presence, which bots cannot access at all for privacy reasons.
"""
import datetime
import random

import database as db
from locales.loader import t
from telegram import Update
from telegram.ext import ContextTypes

ROASTS = [
    "তুমি এতটাই স্পেশাল যে ChatGPT-ও তোমার জন্য আলাদা এরর মেসেজ বানাবে।",
    "তোমার wifi speed-ও তোমার IQ-এর মতো slow।",
    "তুমি ক্লাসের সবচেয়ে unique স্টুডেন্ট — সবার আগে ঘুমাও।",
    "তোমার লজিক দেখে calculator-ও confuse হয়ে যায়।",
    "You bring everyone so much joy... when you leave the room.",
    "I'd explain it again, but I don't have any crayons with me.",
]


def _touch(update: Update):
    u = update.effective_user
    db.upsert_user(u.id, u.username, u.first_name)


def _target_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.first_name
    if context.args:
        return " ".join(context.args).lstrip("@")
    return "someone"


async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    target = _target_name(update, context)
    await update.message.reply_text(f"{t('roast_intro', lang)}\n\n{target}: {random.choice(ROASTS)}")


async def hug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    sender = update.effective_user.first_name
    target = _target_name(update, context)
    await update.message.reply_text(t("hug_msg", lang, sender=sender, target=target))


async def slap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    sender = update.effective_user.first_name
    target = _target_name(update, context)
    await update.message.reply_text(t("slap_msg", lang, sender=sender, target=target))


async def kiss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    sender = update.effective_user.first_name
    target = _target_name(update, context)
    await update.message.reply_text(t("kiss_msg", lang, sender=sender, target=target))


async def deletelog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    chat_id = update.effective_chat.id
    rows = db.get_recent_messages(chat_id, limit=15)
    if not rows:
        await update.message.reply_text(t("deletelog_empty", lang))
        return

    lines = [t("deletelog_title", lang)]
    for r in rows:
        when = datetime.datetime.fromtimestamp(r["sent_at"]).strftime("%H:%M")
        name = r["username"] or str(r["user_id"])
        snippet = (r["text"] or "")[:60]
        lines.append(f"[{when}] {name}: {snippet}")
    await update.message.reply_text("\n".join(lines))


async def lastseen_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /lastseen @username")
        return

    username = context.args[0].lstrip("@")
    try:
        chat = await context.bot.get_chat(f"@{username}")
        ts = db.get_last_seen(chat.id)
        if not ts:
            await update.message.reply_text("📭 No activity recorded yet for this user.")
            return
        when = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        await update.message.reply_text(t("lastseen_msg", lang, name=chat.first_name or username, time=when))
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


async def log_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passive handler (registered with a MessageHandler in bot.py, no
    command) — logs every text message in a group for /deletelog and
    updates the sender's last_seen for /lastseen. Also does simple
    link-preview passthrough (Telegram already auto-previews links, so this
    just makes sure the sender is tracked; no extra action needed there)."""
    msg = update.effective_message
    if not msg or not msg.text or update.effective_chat.type not in ("group", "supergroup"):
        return

    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    db.update_last_seen(user.id)
    db.log_message(update.effective_chat.id, msg.message_id, user.id, user.username or user.first_name, msg.text)

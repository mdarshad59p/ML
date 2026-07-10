"""
Fun-zone commands.

NOTE: /fakesms (fake bKash/Nagad/Rocket transaction SMS) was intentionally
left out of this build. Fake mobile-money "payment sent" screenshots are a
real, common scam vector in Bangladesh — sellers get shown a fake SMS and
hand over goods before checking their actual balance. Everything else in
the original fun-zone list (fakechat, fakewhatsapp, meme, friendship card)
is implemented below.

Argument convention: since names/messages can contain spaces, all multi-field
commands use "|" as the field separator, e.g.:
  /meme drake | top text here | bottom text here
  /fakechat whatsapp | Alice | Bob | hey!|how are you?|good, you?
  /fakewhatsapp Alice | Bob | hey, are we still on for tonight?
  /friendship Alice | Bob
"""
import database as db
from locales.loader import t
from telegram import Update
from telegram.ext import ContextTypes
from utils.image_gen import generate_meme, generate_fake_chat, generate_friendship_card


def _touch(update: Update):
    u = update.effective_user
    db.upsert_user(u.id, u.username, u.first_name)


def _split_args(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
    raw = " ".join(context.args) if context.args else ""
    return [p.strip() for p in raw.split("|") if p.strip() != ""]


MEME_TEMPLATES_HELP = (
    "Usage: /meme <template> | <top text> | <bottom text>\n"
    "Example: /meme drake | old way | new way\n\n"
    "Drop real template images into assets/templates/<name>.jpg to use named "
    "templates — unrecognized names fall back to a plain dark background."
)


async def meme_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    parts = _split_args(context)
    if not parts:
        await update.message.reply_text(MEME_TEMPLATES_HELP)
        return

    template = parts[0] if len(parts) > 0 else "blank"
    top = parts[1] if len(parts) > 1 else ""
    bottom = parts[2] if len(parts) > 2 else ""

    try:
        img = generate_meme(template, top, bottom)
        await update.message.reply_photo(photo=img)
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


FAKECHAT_HELP = (
    "Usage: /fakechat <platform> | <sender> | <receiver> | <msg1>|<msg2>|<msg3>...\n"
    "Example: /fakechat WhatsApp | Alice | Bob | hey!|what's up?|nothing much"
)


async def fakechat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    parts = _split_args(context)
    if len(parts) < 4:
        await update.message.reply_text(FAKECHAT_HELP)
        return

    platform, sender, receiver = parts[0], parts[1], parts[2]
    messages = parts[3:]

    try:
        img = generate_fake_chat(platform, sender, receiver, messages)
        await update.message.reply_photo(photo=img)
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


FAKEWA_HELP = "Usage: /fakewhatsapp <sender> | <receiver> | <message>"


async def fakewhatsapp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    parts = _split_args(context)
    if len(parts) < 3:
        await update.message.reply_text(FAKEWA_HELP)
        return

    sender, receiver, message = parts[0], parts[1], parts[2]
    try:
        img = generate_fake_chat("WhatsApp", sender, receiver, [message])
        await update.message.reply_photo(photo=img)
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


FRIENDSHIP_HELP = "Usage: /friendship <name1> | <name2>"


async def friendship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)
    parts = _split_args(context)
    if len(parts) < 2:
        await update.message.reply_text(FRIENDSHIP_HELP)
        return

    try:
        img = generate_friendship_card(parts[0], parts[1])
        await update.message.reply_photo(photo=img)
    except Exception:
        await update.message.reply_text(t("error_generic", lang))

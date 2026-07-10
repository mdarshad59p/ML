import config
import database as db
from locales.loader import t
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


def _touch_user(update: Update):
    u = update.effective_user
    db.upsert_user(u.id, u.username, u.first_name)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch_user(update)
    user = update.effective_user
    lang = db.get_lang(user.id)

    # handle /start <referral_id> deep link
    if context.args:
        arg = context.args[0]
        if arg.isdigit():
            referrer_id = int(arg)
            if referrer_id != user.id:
                db.register_referral(user.id, referrer_id)

    await update.message.reply_text(t("welcome", lang, name=user.first_name or "friend"))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch_user(update)
    lang = db.get_lang(update.effective_user.id)
    await update.message.reply_text(t("help_title", lang))


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch_user(update)
    lang = db.get_lang(update.effective_user.id)
    buttons = []
    row = []
    for code, name in config.SUPPORTED_LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"setlang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await update.message.reply_text(t("lang_choose", lang), reply_markup=InlineKeyboardMarkup(buttons))


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.split(":", 1)[1]
    if code not in config.SUPPORTED_LANGUAGES:
        return
    db.set_lang(update.effective_user.id, code)
    await query.edit_message_text(t("lang_changed", code, lang=config.SUPPORTED_LANGUAGES[code]))


async def set_bot_commands(application):
    """Populates Telegram's native menu button (bottom-left, next to the
    message box) with the bot's personal/economy commands."""
    commands = [
        ("start", "Start the bot"),
        ("help", "Show help"),
        ("lang", "Change language"),
        ("menu", "Show feature menu"),
        ("profile", "Your profile & coins"),
        ("daily", "Claim daily bonus"),
        ("referral", "Get your referral link"),
        ("meme", "Generate a meme"),
        ("fakechat", "Generate a fake chat screenshot"),
        ("fakewhatsapp", "Generate a fake WhatsApp DM"),
        ("friendship", "Make a friendship card"),
        ("removebg", "Remove background from a photo (reply to it)"),
        ("ocr", "Extract text from a photo (reply to it)"),
        ("voicechange", "Change a voice message (reply to it)"),
        ("whatsong", "Identify a song (reply to the audio)"),
        ("qr", "Generate a QR code"),
        ("password", "Generate a strong password"),
        ("checkpass", "Check password strength"),
        ("crypto", "Crypto price"),
        ("stock", "Stock price"),
        ("namaz", "Prayer times (Bangladesh)"),
        ("news", "Bangladesh top headlines"),
        ("short", "Shorten a URL"),
        ("dp", "Get a user's HD profile photo"),
    ]
    await application.bot.set_my_commands(commands)

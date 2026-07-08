import asyncio

import database as db
from locales.loader import t
from telegram import Update
from telegram.error import Forbidden, BadRequest
from telegram.ext import ContextTypes
from utils.decorators import admin_only


@admin_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_user.id)
    total_users = db.user_count()
    text = f"{t('stats_title', lang)}\n\n👥 Users: {total_users}"
    await update.message.reply_text(text)


def _parse_user_amount(context: ContextTypes.DEFAULT_TYPE):
    """Expects: /addcoins <user_id> <amount>"""
    if len(context.args) < 2:
        return None, None
    uid_str, amount_str = context.args[0], context.args[1]
    if not uid_str.isdigit() or not amount_str.lstrip("-").isdigit():
        return None, None
    return int(uid_str), int(amount_str)


@admin_only
async def addcoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_user.id)
    uid, amount = _parse_user_amount(context)
    if uid is None:
        await update.message.reply_text("Usage: /addcoins <user_id> <amount>")
        return
    db.add_coins(uid, amount)
    await update.message.reply_text(f"✅ Added {amount} coins to {uid}.")


@admin_only
async def removecoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, amount = _parse_user_amount(context)
    if uid is None:
        await update.message.reply_text("Usage: /removecoins <user_id> <amount>")
        return
    db.remove_coins(uid, amount)
    await update.message.reply_text(f"✅ Removed {amount} coins from {uid}.")


@admin_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    user_ids = db.all_user_ids()
    sent = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=message)
            sent += 1
        except (Forbidden, BadRequest):
            pass  # user blocked the bot or chat no longer valid
        await asyncio.sleep(0.05)  # gentle rate-limiting to avoid Telegram flood limits

    await update.message.reply_text(t("broadcast_done", lang, sent=sent, total=len(user_ids)))


@admin_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_user.id)
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    db.set_ban(int(context.args[0]), True)
    await update.message.reply_text(t("ban_success", lang))


@admin_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_user.id)
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    db.set_ban(int(context.args[0]), False)
    await update.message.reply_text(t("unban_success", lang))


@admin_only
async def setprice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_user.id)
    if len(context.args) < 2 or not context.args[-1].isdigit():
        await update.message.reply_text("Usage: /setprice <feature_name> <coins>")
        return
    price = int(context.args[-1])
    feature = " ".join(context.args[:-1])
    db.set_feature_price(feature, price)
    await update.message.reply_text(t("price_set", lang, feature=feature, price=price))

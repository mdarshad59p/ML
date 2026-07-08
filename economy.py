import config
import database as db
from locales.loader import t
from telegram import Update
from telegram.ext import ContextTypes


async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    lang = db.get_lang(user.id)

    if not db.can_claim_daily(user.id):
        await update.message.reply_text(t("daily_already", lang))
        return

    streak = db.claim_daily(user.id)
    await update.message.reply_text(
        t("daily_success", lang, amount=config.DAILY_COIN_REWARD, streak=streak)
    )


async def referral_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    lang = db.get_lang(user.id)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user.id}"
    await update.message.reply_text(
        t("referral_link_msg", lang, link=link, amount=config.REFERRAL_COIN_REWARD)
    )


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    lang = db.get_lang(user.id)
    row = db.get_user(user.id)

    text = (
        f"{t('profile_title', lang)}\n\n"
        f"{t('profile_coins', lang, coins=row['coins'])}\n"
        f"{t('profile_streak', lang, streak=row['streak'])}\n"
        f"{t('profile_referrals', lang, count=row['referral_count'])}"
    )
    await update.message.reply_text(text)

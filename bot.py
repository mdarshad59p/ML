"""
Maya's Lab Bot — main entry point.

Run locally:      python bot.py
Deploy on Render:  see README.md (uses long-polling + a tiny Flask keep-alive
                    server so UptimeRobot can ping it and stop Render's free
                    tier from spinning the instance down).
"""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

import config
import database as db
from handlers import start, economy, fun, media, tools, group, admin

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def _ban_middleware(update: Update, context):
    """Runs before every other handler (group=-1). Silently drops all
    interaction from banned users except letting admins still use /unban."""
    user = update.effective_user
    if user is None:
        return
    if db.is_banned(user.id) and user.id not in config.ADMIN_IDS:
        raise ApplicationHandlerStop


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    application = Application.builder().token(config.BOT_TOKEN).post_init(start.set_bot_commands).build()

    # ban check runs first, for every update
    application.add_handler(TypeHandler(Update, _ban_middleware), group=-1)

    # ---- core ----
    application.add_handler(CommandHandler("start", start.start_cmd))
    application.add_handler(CommandHandler("help", start.help_cmd))
    application.add_handler(CommandHandler("menu", start.help_cmd))
    application.add_handler(CommandHandler("lang", start.lang_cmd))
    application.add_handler(CallbackQueryHandler(start.lang_callback, pattern=r"^setlang:"))

    # ---- economy ----
    application.add_handler(CommandHandler("daily", economy.daily_cmd))
    application.add_handler(CommandHandler("referral", economy.referral_cmd))
    application.add_handler(CommandHandler("profile", economy.profile_cmd))

    # ---- fun zone ----
    application.add_handler(CommandHandler("meme", fun.meme_cmd))
    application.add_handler(CommandHandler("fakechat", fun.fakechat_cmd))
    application.add_handler(CommandHandler("fakewhatsapp", fun.fakewhatsapp_cmd))
    application.add_handler(CommandHandler("friendship", fun.friendship_cmd))
    # NOTE: /fakesms intentionally not implemented — see handlers/fun.py docstring

    # ---- media processing ----
    application.add_handler(CommandHandler("removebg", media.removebg_cmd))
    application.add_handler(CommandHandler("ocr", media.ocr_cmd))
    application.add_handler(CommandHandler("voicechange", media.voicechange_cmd))
    application.add_handler(CommandHandler("whatsong", media.whatsong_cmd))

    # ---- utility tools ----
    application.add_handler(CommandHandler("dp", tools.dp_cmd))
    application.add_handler(CommandHandler("short", tools.short_cmd))
    application.add_handler(CommandHandler("webss", tools.webss_cmd))
    application.add_handler(CommandHandler("filetolink", tools.filetolink_cmd))
    application.add_handler(CommandHandler("qr", tools.qr_cmd))
    application.add_handler(CommandHandler("namaz", tools.namaz_cmd))
    application.add_handler(CommandHandler("crypto", tools.crypto_cmd))
    application.add_handler(CommandHandler("stock", tools.stock_cmd))
    application.add_handler(CommandHandler("password", tools.password_cmd))
    application.add_handler(CommandHandler("checkpass", tools.checkpass_cmd))
    application.add_handler(CommandHandler("news", tools.news_cmd))

    # ---- group tools ----
    application.add_handler(CommandHandler("roast", group.roast_cmd))
    application.add_handler(CommandHandler("hug", group.hug_cmd))
    application.add_handler(CommandHandler("slap", group.slap_cmd))
    application.add_handler(CommandHandler("kiss", group.kiss_cmd))
    application.add_handler(CommandHandler("deletelog", group.deletelog_cmd))
    application.add_handler(CommandHandler("lastseen", group.lastseen_cmd))
    # passive logger for /deletelog + /lastseen — must not swallow other commands
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, group.log_all_messages)
    )

    # ---- admin panel ----
    application.add_handler(CommandHandler("stats", admin.stats_cmd))
    application.add_handler(CommandHandler("addcoins", admin.addcoins_cmd))
    application.add_handler(CommandHandler("removecoins", admin.removecoins_cmd))
    application.add_handler(CommandHandler("broadcast", admin.broadcast_cmd))
    application.add_handler(CommandHandler("ban", admin.ban_cmd))
    application.add_handler(CommandHandler("unban", admin.unban_cmd))
    application.add_handler(CommandHandler("setprice", admin.setprice_cmd))

    return application


def main():
    db.init_db()

    # keep-alive web server for Render free tier + UptimeRobot (safe no-op locally too)
    try:
        from utils.keep_alive import start_keep_alive
        start_keep_alive()
    except Exception as e:
        logger.warning(f"Keep-alive server did not start: {e}")

    application = build_application()
    logger.info("Maya's Lab Bot starting (long polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

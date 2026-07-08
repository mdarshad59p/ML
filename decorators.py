"""
Reusable decorators for handlers:
- admin_only: restricts a command to config.ADMIN_IDS
- track_user: upserts the user + updates last_seen on every command (call manually at top of handler, simpler than a decorator here since PTB handlers are async)
- require_coins: checks + deducts coins based on feature_prices table
"""
import functools

import config
import database as db
from locales.loader import t


def admin_only(func):
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_IDS:
            lang = db.get_lang(user_id)
            await update.effective_message.reply_text(t("admin_only", lang))
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


def block_banned(func):
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if db.is_banned(user_id):
            lang = db.get_lang(user_id)
            await update.effective_message.reply_text(t("banned_user", lang))
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


def require_coins(feature_name: str):
    """Decorator factory: checks user has enough coins for `feature_name`,
    and deducts them if so. Skips the check entirely if price is 0."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            price = db.get_feature_price(feature_name)
            if price > 0:
                coins = db.get_coins(user_id)
                lang = db.get_lang(user_id)
                if coins < price:
                    await update.effective_message.reply_text(
                        t("not_enough_coins", lang, price=price, coins=coins)
                    )
                    return
                db.remove_coins(user_id, price)
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator

"""
Render's free web-service tier spins the instance down after ~15 minutes with
no HTTP traffic, which would kill a long-polling Telegram bot too. The fix:
run a tiny Flask server on config.PORT alongside the bot, and point
UptimeRobot (or any pinger) at it every 5 minutes to keep the instance awake.

This runs in a background thread so it doesn't block python-telegram-bot's
own event loop.
"""
import threading
import time

from flask import Flask

import config

app = Flask(__name__)
_start_time = time.time()


@app.route("/")
def home():
    uptime = int(time.time() - _start_time)
    return {"status": "ok", "bot": "Maya's Lab Bot", "uptime_seconds": uptime}


@app.route("/health")
def health():
    return {"status": "healthy"}


def run():
    app.run(host="0.0.0.0", port=config.PORT)


def start_keep_alive():
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# Maya's Lab Bot 🎭

Python (`python-telegram-bot` v21) Telegram bot — memes, fun tools, image/audio
utilities, an economy system, admin panel, and 10-language support.

## ⚠️ What's NOT included, and why

**`/fakesms`** (a command that would generate fake bKash/Nagad/Rocket "money
received" SMS screenshots) was intentionally left out of this build. Fake
mobile-money transaction alerts are a real, common scam pattern in
Bangladesh — a buyer shows a seller a fake "payment sent" SMS and the seller
hands over goods without checking their actual balance. Every other feature
from the original spec is implemented.

## 🗂 Project structure

```
maya_lab_bot/
├── bot.py                 # entry point — registers all handlers
├── config.py               # env var loading
├── database.py              # SQLite: users, coins, bans, message log
├── requirements.txt
├── Dockerfile               # use this for Render (gets tesseract/ffmpeg/zbar)
├── render.yaml               # Render blueprint
├── .env.example
├── locales/                 # bn, en, hi, ur, ar, es, id, ru, zh, fr
│   ├── loader.py
│   └── *.json
├── handlers/
│   ├── start.py             # /start /help /lang + native menu button setup
│   ├── economy.py           # /daily /referral /profile
│   ├── fun.py                # /meme /fakechat /fakewhatsapp /friendship
│   ├── media.py               # /removebg /ocr /voicechange /whatsong
│   ├── tools.py                # /dp /short /webss /filetolink /qr /namaz
│   │                             # /crypto /stock /password /checkpass /news
│   ├── group.py                 # /roast /hug /slap /kiss /deletelog /lastseen
│   └── admin.py                  # /stats /addcoins /removecoins /broadcast
│                                   # /ban /unban /setprice
├── utils/
│   ├── decorators.py         # admin_only, block_banned, require_coins
│   ├── image_gen.py           # Pillow: meme / fake chat / friendship card
│   └── keep_alive.py           # Flask server for Render + UptimeRobot
└── assets/
    ├── fonts/README.txt        # add a Bangla-capable .ttf here (see below)
    └── templates/README.txt     # add real meme template images here
```

## 🚀 Local setup

```bash
git clone <your-repo>
cd maya_lab_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then edit .env: set BOT_TOKEN and ADMIN_IDS
python bot.py
```

Get `BOT_TOKEN` from [@BotFather](https://t.me/BotFather). `ADMIN_IDS` is
your numeric Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot)).

**System dependencies for full functionality (only matters for `/ocr`,
`/voicechange`, `/qr` reading):**
```bash
sudo apt install tesseract-ocr tesseract-ocr-ben ffmpeg libzbar0
```
Everything else works with just `pip install -r requirements.txt`.

## ☁️ Deploying on Render (free tier) + UptimeRobot

1. Push this project to GitHub.
2. On [render.com](https://render.com) → New → Web Service → connect your repo.
3. **Environment: choose "Docker"** (not the Python native buildpack) — the
   included `Dockerfile` installs tesseract/ffmpeg/libzbar for you.
4. Add environment variables from `.env.example` in Render's dashboard
   (Environment tab). At minimum: `BOT_TOKEN`, `ADMIN_IDS`.
5. Deploy. Render gives you a URL like `https://maya-lab-bot.onrender.com`.
6. On [uptimerobot.com](https://uptimerobot.com), add an **HTTP(s) monitor**
   pointed at that URL, checking every 5 minutes. This keeps Render's free
   instance from sleeping — the bot's keep-alive server (`utils/keep_alive.py`)
   responds to these pings automatically.

The bot itself runs via **long polling** (not webhooks), so no webhook
configuration is required — it just needs the process to stay alive, which
is what the keep-alive server + UptimeRobot combo handles.

## 🌍 Languages

10 languages are supported (`bn`, `en`, `hi`, `ur`, `ar`, `es`, `id`, `ru`,
`zh`, `fr`) — users switch anytime with `/lang`. Default is English
(`config.DEFAULT_LANGUAGE`); change to `"bn"` in `config.py` if you'd rather
default to Bangla. All 10 locale files have the full UI string set
translated — extend `locales/*.json` with more keys as you add features.

## 🔑 Features that need a free API key to fully work

Without these, the bot still runs fine — the command just replies "not
configured yet" until you add the key to `.env` / Render's environment vars.

| Command | Service | Free tier? |
|---|---|---|
| `/removebg` | [remove.bg](https://www.remove.bg/api) | limited free credits |
| `/whatsong` | [audd.io](https://audd.io) | limited free credits |
| `/stock` | [Alpha Vantage](https://www.alphavantage.co) | free key, rate-limited |
| `/webss` | [screenshotmachine.com](https://screenshotmachine.com) | limited free credits |
| `/news` | [newsapi.org](https://newsapi.org) | free for dev use |

Everything else (`/short`, `/filetolink`, `/namaz`, `/crypto`, `/qr`,
`/ocr`, `/voicechange`, memes, economy, admin panel) works with **no key at
all**.

## ⚠️ Two honest technical limitations

1. **`/deletelog` does not catch real-time deletions.** The Telegram Bot API
   has no event for "a user deleted a message" — that's only visible to full
   MTProto user sessions, not bots. What this actually does is log the last
   ~500 messages per group and show that as an activity log. Don't advertise
   it to your users as a live delete-catcher — it isn't one.
2. **`/lastseen` is best-effort.** It only updates when the bot sees a
   message from that user in a shared chat — bots cannot access Telegram's
   real online/offline presence at all (by design, for privacy).

## 🔤 Non-Latin text in generated images

`/meme`, `/fakechat`, `/friendship` use Pillow to draw text. The bundled
font (DejaVu Sans Bold) only covers Latin/Cyrillic/Greek. For Bangla/Hindi/
Urdu/Arabic captions to render instead of empty boxes, add a matching font —
see `assets/fonts/README.txt`.

## 💰 Economy defaults

Daily bonus: +20 coins (`config.DAILY_COIN_REWARD`). Referral bonus: +15
coins per invite (`config.REFERRAL_COIN_REWARD`). Admins can price-gate any
feature with `/setprice <feature_name> <coins>` — the `require_coins()`
decorator in `utils/decorators.py` is ready to wrap any handler if you want
to enforce it (not yet applied to any command by default, so nothing costs
coins out of the box — wire it in wherever you want).

## 📋 Full command list

See the table in the original spec — all commands are implemented under
the categories above except `/fakesms` (see top of this file).

"""
Image/audio processing commands. All of these need the user to REPLY to a
photo/voice/audio message with the command.

- /removebg : needs REMOVEBG_API_KEY (remove.bg). Without a key, replies
  "not configured".
- /ocr      : fully local via pytesseract + tesseract-ocr binary. No key needed,
  but the tesseract binary must be installed on the host (see README /
  Dockerfile — it's on this dev sandbox but Render needs a Dockerfile to get it).
- /voicechange : local via pydub + ffmpeg (also needs the ffmpeg binary present).
  Effects implemented: cartoon (pitch up), robot (echo/robotic), girl (pitch up + speed).
- /whatsong : needs AUDD_API_KEY (audd.io). Without a key, replies "not configured".
"""
import io

import requests
from PIL import Image
import pytesseract

import config
import database as db
from locales.loader import t
from telegram import Update
from telegram.ext import ContextTypes


def _touch(update: Update):
    u = update.effective_user
    db.upsert_user(u.id, u.username, u.first_name)


async def removebg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("↩️ Reply to a photo with /removebg")
        return

    if not config.REMOVEBG_API_KEY:
        await update.message.reply_text(t("feature_not_configured", lang))
        return

    photo = update.message.reply_to_message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()

    try:
        resp = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            files={"image_file": bytes(photo_bytes)},
            data={"size": "auto"},
            headers={"X-Api-Key": config.REMOVEBG_API_KEY},
            timeout=30,
        )
        if resp.status_code == 200:
            await update.message.reply_photo(photo=io.BytesIO(resp.content))
        else:
            await update.message.reply_text(t("error_generic", lang))
    except requests.RequestException:
        await update.message.reply_text(t("error_generic", lang))


async def ocr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("↩️ Reply to a photo with /ocr")
        return

    photo = update.message.reply_to_message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()

    try:
        img = Image.open(io.BytesIO(bytes(photo_bytes)))
        # lang="ben+eng" also tries Bangla if the tesseract-ocr-ben package
        # is installed on the host; falls back gracefully to eng-only otherwise.
        try:
            text = pytesseract.image_to_string(img, lang="ben+eng")
        except pytesseract.TesseractError:
            text = pytesseract.image_to_string(img)
        text = text.strip()
        await update.message.reply_text(text if text else "📭 No text detected.")
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


VOICE_STYLES = {"cartoon", "robot", "girl"}


async def voicechange_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    if not update.message.reply_to_message or not (
        update.message.reply_to_message.voice or update.message.reply_to_message.audio
    ):
        await update.message.reply_text(
            "↩️ Reply to a voice/audio message with /voicechange <cartoon|robot|girl>"
        )
        return

    style = (context.args[0].lower() if context.args else "cartoon")
    if style not in VOICE_STYLES:
        await update.message.reply_text(f"Style must be one of: {', '.join(VOICE_STYLES)}")
        return

    try:
        from pydub import AudioSegment  # imported lazily; needs ffmpeg on the host
    except ImportError:
        await update.message.reply_text(t("feature_not_configured", lang))
        return

    voice = update.message.reply_to_message.voice or update.message.reply_to_message.audio
    file = await voice.get_file()
    raw_bytes = await file.download_as_bytearray()

    try:
        audio = AudioSegment.from_file(io.BytesIO(bytes(raw_bytes)))

        if style == "cartoon" or style == "girl":
            # crude pitch-up: speed up playback rate, then relabel frame rate
            octaves = 0.35 if style == "cartoon" else 0.2
            new_rate = int(audio.frame_rate * (2.0 ** octaves))
            shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
            processed = shifted.set_frame_rate(audio.frame_rate)
        else:  # robot: layer a slightly delayed, quieter copy for a robotic/echo feel
            delayed = AudioSegment.silent(duration=25) + (audio - 8)
            processed = audio.overlay(delayed)

        out_buf = io.BytesIO()
        processed.export(out_buf, format="ogg", codec="libopus")
        out_buf.seek(0)
        out_buf.name = "voice.ogg"
        await update.message.reply_voice(voice=out_buf)
    except Exception:
        await update.message.reply_text(t("error_generic", lang))


async def whatsong_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _touch(update)
    lang = db.get_lang(update.effective_user.id)

    if not update.message.reply_to_message or not (
        update.message.reply_to_message.voice
        or update.message.reply_to_message.audio
        or update.message.reply_to_message.video_note
    ):
        await update.message.reply_text("↩️ Reply to an audio/voice clip with /whatsong")
        return

    if not config.AUDD_API_KEY:
        await update.message.reply_text(t("feature_not_configured", lang))
        return

    media = (
        update.message.reply_to_message.voice
        or update.message.reply_to_message.audio
        or update.message.reply_to_message.video_note
    )
    file = await media.get_file()
    raw_bytes = await file.download_as_bytearray()

    try:
        resp = requests.post(
            "https://api.audd.io/",
            data={"api_token": config.AUDD_API_KEY, "return": "apple_music,spotify"},
            files={"file": bytes(raw_bytes)},
            timeout=30,
        )
        data = resp.json()
        result = data.get("result")
        if not result:
            await update.message.reply_text("🤷 Couldn't identify that song.")
            return
        title = result.get("title", "?")
        artist = result.get("artist", "?")
        await update.message.reply_text(f"🎵 {title} — {artist}")
    except (requests.RequestException, ValueError):
        await update.message.reply_text(t("error_generic", lang))

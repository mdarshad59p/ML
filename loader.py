"""
Loads locale JSON files and provides a simple t(key, lang, **kwargs) translate
function with automatic fallback to English if a key/language is missing.
"""
import json
import os

_DIR = os.path.dirname(__file__)
_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _cache:
        path = os.path.join(_DIR, f"{lang}.json")
        if not os.path.exists(path):
            lang = "en"
            path = os.path.join(_DIR, "en.json")
        with open(path, "r", encoding="utf-8") as f:
            _cache[lang] = json.load(f)
    return _cache[lang]


def t(key: str, lang: str = "en", **kwargs) -> str:
    data = _load(lang)
    text = data.get(key)
    if text is None:
        # fallback to English if this language is missing a key
        text = _load("en").get(key, key)
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text

from __future__ import annotations

from app.bot.utils.ui import DEFAULT_LANG


def get_lang(actor_user=None) -> str:
    lang = getattr(actor_user, 'lang', None)
    if lang in {'uz', 'ru'}:
        return lang
    return DEFAULT_LANG

from __future__ import annotations

from app.bot.keyboards.common import action_kb, tx


def start_kb(lang: str = "uz"):
    return action_kb([
        [tx("start.parent_login", lang)],
        [tx("start.employee_login", lang)],
        ["🌐 Til / Язык"],
    ], lang=lang, with_cancel=False)

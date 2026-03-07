from __future__ import annotations

from app.bot.keyboards.common import action_kb, tx


def teacher_menu_kb(lang: str = "uz"):
    return action_kb([
        [tx("menu.teacher.grades", lang), tx("menu.teacher.homework", lang)],
        [tx("menu.teacher.complaint", lang), tx("menu.teacher.faceid", lang)],
        ["🌐 Til / Язык"],
    ], lang=lang, with_cancel=False, with_home=True)

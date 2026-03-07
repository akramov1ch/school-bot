from __future__ import annotations

from app.bot.keyboards.common import action_kb, tx


def parent_menu_kb(lang: str = "uz"):
    return action_kb([
        [tx("menu.parent.children", lang), tx("menu.parent.add_child", lang)],
        [tx("menu.parent.grades", lang), tx("menu.parent.homeworks", lang)],
        [tx("menu.parent.payments", lang), tx("menu.parent.feedback", lang)],
        ["🌐 Til / Язык"],
    ], lang=lang, with_cancel=False, with_home=True)

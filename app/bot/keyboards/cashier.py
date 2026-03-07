from __future__ import annotations

from app.bot.keyboards.common import action_kb, tx


def cashier_menu_kb(lang: str = "uz"):
    return action_kb([
        [tx("menu.cashier.create", lang), tx("menu.cashier.search", lang)],
        [tx("menu.cashier.faceid", lang)],
        ["🌐 Til / Язык"],
    ], lang=lang, with_cancel=False, with_home=True)

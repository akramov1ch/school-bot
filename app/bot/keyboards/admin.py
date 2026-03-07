from __future__ import annotations

from app.bot.keyboards.common import action_kb, tx


def admin_menu_kb(lang: str = "uz"):
    return action_kb([
        [tx("menu.admin.sync", lang), tx("menu.admin.class_subject", lang)],
        [tx("menu.admin.reset", lang), tx("menu.admin.feedback", lang)],
        [tx("menu.admin.audit", lang), tx("menu.admin.faceid", lang)],
        [tx("menu.admin.faceid_selfie", lang)],
        ["🌐 Til / Язык"],
    ], lang=lang, with_cancel=False, with_home=True)

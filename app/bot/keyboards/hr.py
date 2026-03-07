from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.keyboards.common import action_kb, tx


def hr_menu_kb(lang: str = "uz"):
    return action_kb([
        [tx("menu.hr.employees", lang), tx("menu.hr.status", lang)],
        [tx("menu.hr.reset", lang), tx("menu.hr.faceid", lang)],
        ["🌐 Til / Язык"],
    ], lang=lang, with_cancel=False, with_home=True)


def hr_status_inline_kb(prefix: str = "hr_status", *, lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Faol", callback_data=f"{prefix}:active"),
                InlineKeyboardButton(text="⛔ Nofaol", callback_data=f"{prefix}:inactive"),
            ],
            [InlineKeyboardButton(text=tx("common.cancel", lang), callback_data=f"{prefix}:cancel")],
        ]
    )

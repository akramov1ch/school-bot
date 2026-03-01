from __future__ import annotations

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def hr_menu_kb() -> ReplyKeyboardMarkup:
    """
    HR menyu (Reply keyboard).
    Router'da: reply_markup=hr_menu_kb()
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Xodimlar")],
            [KeyboardButton(text="🔁 Holat o‘zgartirish")],
            [KeyboardButton(text="🔐 Parol tiklash")],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def hr_status_inline_kb(prefix: str = "hr_status") -> InlineKeyboardMarkup:
    """
    Active/Inactive tanlash uchun inline keyboard.
    Router'da:
      reply_markup=hr_status_inline_kb()
    Callback data:
      hr_status:active | hr_status:inactive | hr_status:cancel
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Active", callback_data=f"{prefix}:active"),
                InlineKeyboardButton(text="⛔ Inactive", callback_data=f"{prefix}:inactive"),
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}:cancel"),
            ],
        ]
    )
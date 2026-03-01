from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="🔄 Manual sync"))
    kb.add(KeyboardButton(text="🧩 Class-Subject-Teacher"))
    kb.add(KeyboardButton(text="🔐 Credential reset"))
    kb.add(KeyboardButton(text="📥 Feedback inbox"))
    kb.add(KeyboardButton(text="🕵️ Audit log"))
    kb.add(KeyboardButton(text="🧑‍🔧 FaceID admin"))
    kb.add(KeyboardButton(text="📷 Selfie (FaceID)")) # Yangi tugma
    kb.add(KeyboardButton(text="🏠 Bosh menyu"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)
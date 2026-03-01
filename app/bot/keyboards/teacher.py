from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def teacher_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📌 Ballar"))
    kb.add(KeyboardButton(text="✍️ Uyga vazifa"))
    kb.add(KeyboardButton(text="✉️ Shikoyat"))
    kb.add(KeyboardButton(text="📷 Selfie (FaceID)"))
    kb.add(KeyboardButton(text="🏠 Bosh меню"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)
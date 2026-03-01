from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def parent_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="➕ O‘quvchi qo‘shish"))
    kb.add(KeyboardButton(text="👶 Farzandlarim"))
    kb.add(KeyboardButton(text="📊 Natijalar"))
    kb.add(KeyboardButton(text="✍️ Uyga vazifalar"))
    kb.add(KeyboardButton(text="💳 To‘lovlar tarixi"))
    kb.add(KeyboardButton(text="📝 Taklif/Shikoyat"))
    kb.add(KeyboardButton(text="🏠 Bosh меню"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)
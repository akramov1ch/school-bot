from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def start_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="👨‍👩‍👧 Ota-ona sifatida kirish"))
    kb.add(KeyboardButton(text="🧑‍💼 Xodim sifatida kirish"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)
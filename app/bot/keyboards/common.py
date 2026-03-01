from __future__ import annotations

from typing import List, Tuple, Any
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def back_kb(text: str = "⬅️ Orqaga") -> ReplyKeyboardMarkup:
    """Oddiy 'Orqaga' tugmasi (Reply)"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=text))
    return kb.as_markup(resize_keyboard=True)


def yes_no_kb(yes: str = "✅ Ha", no: str = "❌ Yo‘q") -> ReplyKeyboardMarkup:
    """Tasdiqlash tugmalari (Reply)"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=yes))
    kb.add(KeyboardButton(text=no))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def inline_items(items: list[tuple[str, str]], columns: int = 2) -> InlineKeyboardMarkup:
    """
    Oldindan ma'lum bo'lgan statik ro'yxatdan Inline tugmalar yasash.
    items: [("Tugma matni", "callback_data"), ...]
    """
    b = InlineKeyboardBuilder()
    for text, cb in items:
        b.add(InlineKeyboardButton(text=text, callback_data=cb))
    b.adjust(columns)
    return b.as_markup()


def dynamic_inline_kb(items: List[Any], prefix: str, columns: int = 2) -> InlineKeyboardMarkup:
    """
    Bazadan kelgan ro'yxat asosida dinamik Inline tugmalar yasash.
    
    :param items: Tugma matni bo'ladigan elementlar ro'yxati (masalan: ["5-A", "6-B"])
    :param prefix: Callback data uchun prefiks (masalan: "select_class")
    :param columns: Tugmalar necha ustun bo'lishi
    :return: InlineKeyboardMarkup
    
    Natija callback_data ko'rinishi: "select_class:5-A"
    """
    builder = InlineKeyboardBuilder()
    for item in items:
        # Element string bo'lsa o'zi, obyekt bo'lsa uning nomi olinadi
        text = str(item)
        # Callback data uzunligi 64 baytdan oshmasligi kerak
        callback_data = f"{prefix}:{text}"
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(columns)
    return builder.as_markup()


def cancel_inline_kb(text: str = "❌ Bekor qilish", callback: str = "cancel_action") -> InlineKeyboardMarkup:
    """Jarayonni bekor qilish uchun Inline tugma"""
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=callback)
    return builder.as_markup()
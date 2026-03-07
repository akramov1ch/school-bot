from __future__ import annotations

from math import ceil
from typing import List, Any, Iterable
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.i18n import t


def tx(key: str, lang: str = "uz", **kwargs) -> str:
    return t(key, lang, **kwargs)


def _reply_markup(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for row in rows:
        for text in row:
            kb.add(KeyboardButton(text=text))
    if rows:
        kb.adjust(*[len(r) for r in rows])
    return kb.as_markup(resize_keyboard=True, is_persistent=True)


def action_kb(rows: list[list[str]], *, lang: str = "uz", with_cancel: bool = True, with_home: bool = False) -> ReplyKeyboardMarkup:
    items = [*rows]
    footer: list[str] = []
    if with_cancel:
        footer.append(tx("common.cancel", lang))
    if with_home:
        footer.append(tx("common.home", lang))
    if footer:
        items.append(footer)
    return _reply_markup(items)


def back_kb(*, lang: str = "uz", text: str | None = None) -> ReplyKeyboardMarkup:
    return action_kb([[text or tx("common.back", lang)]], lang=lang, with_cancel=False)


def yes_no_kb(*, lang: str = "uz", yes: str | None = None, no: str | None = None, with_cancel: bool = True) -> ReplyKeyboardMarkup:
    return action_kb([[yes or tx("common.yes", lang), no or tx("common.no", lang)]], lang=lang, with_cancel=with_cancel)


def inline_items(items: list[tuple[str, str]], columns: int = 2, *, add_cancel: bool = False, lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for text, cb in items:
        b.add(InlineKeyboardButton(text=text, callback_data=cb))
    if add_cancel:
        b.add(InlineKeyboardButton(text=tx("common.cancel", lang), callback_data="cancel_action"))
    b.adjust(columns)
    return b.as_markup()


def dynamic_inline_kb(items: List[Any], prefix: str, columns: int = 2, *, add_cancel: bool = True, lang: str = "uz") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        text = str(item)
        callback_data = f"{prefix}:{text}"
        builder.button(text=text, callback_data=callback_data)
    if add_cancel:
        builder.button(text=tx("common.cancel", lang), callback_data="cancel_action")
    builder.adjust(columns)
    return builder.as_markup()


def cancel_inline_kb(*, lang: str = "uz", text: str | None = None, callback: str = "cancel_action") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text or tx("common.cancel", lang), callback_data=callback)
    return builder.as_markup()


def paginated_inline_kb(
    items: Iterable[tuple[str, str]],
    *,
    page: int = 0,
    per_page: int = 8,
    nav_prefix: str,
    columns: int = 1,
    lang: str = "uz",
    add_search: bool = False,
    add_cancel: bool = True,
) -> InlineKeyboardMarkup:
    item_list = list(items)
    total_pages = max(1, ceil(len(item_list) / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = start + per_page

    builder = InlineKeyboardBuilder()
    for text, cb in item_list[start:end]:
        builder.button(text=text, callback_data=cb)

    nav_row: list[InlineKeyboardButton] = []
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=tx("list.prev", lang), callback_data=f"{nav_prefix}:page:{max(page - 1, 0)}"))
        nav_row.append(InlineKeyboardButton(text=tx("list.page", lang, current=page + 1, total=total_pages), callback_data="noop"))
        nav_row.append(InlineKeyboardButton(text=tx("list.next", lang), callback_data=f"{nav_prefix}:page:{min(page + 1, total_pages - 1)}"))
        builder.row(*nav_row)

    if add_search:
        builder.row(InlineKeyboardButton(text=tx("common.search", lang), callback_data=f"{nav_prefix}:search"))
    if add_cancel:
        builder.row(InlineKeyboardButton(text=tx("common.cancel", lang), callback_data="cancel_action"))

    builder.adjust(columns)
    return builder.as_markup()

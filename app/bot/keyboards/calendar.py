from __future__ import annotations

from calendar import monthrange
from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.common import tx

MONTHS = {
    'uz': ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'],
    'ru': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
}
WEEKDAYS = {
    'uz': ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'],
    'ru': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
}


def calendar_kb(*, year: int | None = None, month: int | None = None, prefix: str = 'cal', lang: str = 'uz', include_today: bool = True) -> InlineKeyboardMarkup:
    today = date.today()
    year = year or today.year
    month = month or today.month
    first_weekday, days_in_month = monthrange(year, month)
    # monthrange: Monday=0

    b = InlineKeyboardBuilder()
    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year

    title = f"{MONTHS.get(lang, MONTHS['uz'])[month - 1]} {year}"
    b.row(
        InlineKeyboardButton(text='⬅️', callback_data=f'{prefix}:nav:{prev_year}:{prev_month}'),
        InlineKeyboardButton(text=title, callback_data='noop'),
        InlineKeyboardButton(text='➡️', callback_data=f'{prefix}:nav:{next_year}:{next_month}'),
    )
    b.row(*[InlineKeyboardButton(text=wd, callback_data='noop') for wd in WEEKDAYS.get(lang, WEEKDAYS['uz'])])

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(text=' ', callback_data='noop'))
    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        label = str(day)
        if current == today:
            label = f'•{day}'
        row.append(InlineKeyboardButton(text=label, callback_data=f'{prefix}:pick:{current.isoformat()}'))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(text=' ', callback_data='noop'))
        rows.append(row)
    for r in rows:
        b.row(*r)

    footer = []
    if include_today:
        footer.append(InlineKeyboardButton(text=tx('common.today', lang), callback_data=f'{prefix}:pick:{today.isoformat()}'))
    footer.append(InlineKeyboardButton(text=tx('common.cancel', lang), callback_data='cancel_action'))
    b.row(*footer)
    return b.as_markup()

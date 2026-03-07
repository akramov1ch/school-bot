from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.common import tx, inline_items
from app.bot.utils.ui import role_menu, DEFAULT_LANG
from app.bot.utils.lang import get_lang
from app.models.enums import UserRole
from app.core.logging import get_logger
from app.core.db import get_sessionmaker
from app.repositories.users import UserRepository

router = Router()
logger = get_logger(__name__)

CANCEL_WORDS = {
    tx("common.cancel", "uz"), tx("common.cancel", "ru"),
    "bekor", "cancel", "/cancel", "отмена",
}
HOME_WORDS = {
    tx("common.home", "uz"), tx("common.home", "ru"),
    "bosh menyu", "/start", "главное меню",
}


async def _resolve_lang(telegram_id: int, actor_user=None) -> str:
    lang = get_lang(actor_user)
    if lang != DEFAULT_LANG or actor_user is not None:
        return lang
    async with get_sessionmaker()() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        return getattr(user, 'lang', None) or DEFAULT_LANG


async def _ask_language(target: Message | CallbackQuery, current_lang: str = DEFAULT_LANG):
    markup = inline_items([
        (tx('common.lang_uz', current_lang), 'lang:set:uz'),
        (tx('common.lang_ru', current_lang), 'lang:set:ru'),
    ], columns=1, add_cancel=False, lang=current_lang)
    if isinstance(target, Message):
        await target.answer(tx('start.choose_lang', current_lang), reply_markup=markup)
    else:
        await target.message.answer(tx('start.choose_lang', current_lang), reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message, actor_role: UserRole, actor_user, state: FSMContext, **_):
    await state.clear()
    lang = await _resolve_lang(message.from_user.id, actor_user)
    if actor_user is None or getattr(actor_user, 'lang', None) in (None, ''):
        await _ask_language(message, lang)
        return
    text, markup = role_menu(actor_role, lang)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith('lang:set:'))
async def set_language(callback: CallbackQuery, actor_role: UserRole, actor_user, state: FSMContext, **_):
    await state.clear()
    lang = (callback.data or '').split(':')[-1]
    if lang not in {'uz', 'ru'}:
        await callback.answer()
        return
    async with get_sessionmaker()() as session:
        repo = UserRepository(session)
        await repo.set_lang(callback.from_user.id, lang)
        await session.commit()
    text, markup = role_menu(actor_role, lang)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(tx('start.lang_saved', lang))
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.message(F.text == '🌐 Til / Язык')
async def choose_language_again(message: Message, actor_user=None, **_):
    lang = get_lang(actor_user)
    await _ask_language(message, lang)


@router.message(F.text.in_(HOME_WORDS))
async def go_home(message: Message, actor_role: UserRole, actor_user, state: FSMContext, **_):
    await state.clear()
    lang = await _resolve_lang(message.from_user.id, actor_user)
    text, markup = role_menu(actor_role, lang)
    await message.answer(text, reply_markup=markup)


@router.message(F.text.in_(CANCEL_WORDS))
async def cancel_any_flow(message: Message, actor_role: UserRole, actor_user, state: FSMContext, **_):
    await state.clear()
    lang = await _resolve_lang(message.from_user.id, actor_user)
    text, markup = role_menu(actor_role, lang)
    await message.answer(tx("common.cancelled", lang))
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "cancel_action")
async def cancel_inline_flow(callback: CallbackQuery, actor_role: UserRole, actor_user, state: FSMContext, **_):
    await state.clear()
    lang = await _resolve_lang(callback.from_user.id, actor_user)
    text, markup = role_menu(actor_role, lang)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(tx("common.cancelled", lang))
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer(tx('common.cancel', lang))


@router.callback_query(F.data == 'noop')
async def noop_callback(callback: CallbackQuery):
    await callback.answer()

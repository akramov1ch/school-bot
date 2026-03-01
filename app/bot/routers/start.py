from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.start import start_kb
from app.bot.keyboards.parent import parent_menu_kb
from app.bot.keyboards.teacher import teacher_menu_kb
from app.bot.keyboards.cashier import cashier_menu_kb
from app.bot.keyboards.hr import hr_menu_kb
from app.bot.keyboards.admin import admin_menu_kb
from app.models.enums import UserRole
from app.core.logging import get_logger

router = Router()
logger = get_logger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, actor_role: UserRole, **_):
    if actor_role == UserRole.PARENT:
        await message.answer("🏠 Bosh меню", reply_markup=parent_menu_kb())
        return
    if actor_role == UserRole.TEACHER:
        await message.answer("🏠 Bosh меню", reply_markup=teacher_menu_kb())
        return
    if actor_role == UserRole.CASHIER:
        await message.answer("🏠 Bosh меню", reply_markup=cashier_menu_kb())
        return
    if actor_role == UserRole.HR:
        await message.answer("🏠 Bosh меню", reply_markup=hr_menu_kb())
        return
    if actor_role == UserRole.ADMIN:
        await message.answer("🏠 Bosh меню", reply_markup=admin_menu_kb())
        return

    await message.answer(
        "Assalomu alaykum! Kirish turini tanlang:",
        reply_markup=start_kb(),
    )


@router.message(F.text == "🏠 Bosh меню")
async def go_home(message: Message, actor_role: UserRole, **_):
    if actor_role == UserRole.PARENT:
        await message.answer("🏠 Bosh меню", reply_markup=parent_menu_kb())
    elif actor_role == UserRole.TEACHER:
        await message.answer("🏠 Bosh меню", reply_markup=teacher_menu_kb())
    elif actor_role == UserRole.CASHIER:
        await message.answer("🏠 Bosh меню", reply_markup=cashier_menu_kb())
    elif actor_role == UserRole.HR:
        await message.answer("🏠 Bosh меню", reply_markup=hr_menu_kb())
    elif actor_role == UserRole.ADMIN:
        await message.answer("🏠 Bosh меню", reply_markup=admin_menu_kb())
    else:
        await message.answer("Assalomu alaykum! Kirish turini tanlang:", reply_markup=start_kb())
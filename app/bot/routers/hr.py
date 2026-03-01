from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.hr import hr_menu_kb
from app.bot.states.hr import HrEmployeeStatusFlow, HrResetPasswordFlow
from app.core.logging import get_logger
from app.core.utils import is_employee_uid, normalize_uid
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


def _status_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Active", callback_data="hr_status:active"),
                InlineKeyboardButton(text="⛔ Inactive", callback_data="hr_status:inactive"),
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="hr_status:cancel"),
            ],
        ]
    )


@router.message(F.text == "👥 Xodimlar")
async def hr_list(message: Message, actor_role: UserRole, **_):
    if actor_role not in (UserRole.HR, UserRole.ADMIN):
        await message.answer("❌ Ruxsat yo‘q.")
        return

    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        repo = EmployeeRepository(session)
        items = await repo.list(limit=30)

    if not items:
        await message.answer("Xodimlar topilmadi.")
        return

    lines = ["👥 Xodimlar (top 30):\n"]
    for e in items:
        lines.append(f"• {e.full_name} — {e.employee_uid} | {e.role} | {e.status}")
    await message.answer("\n".join(lines), reply_markup=hr_menu_kb())


@router.message(F.text == "🔁 Holat o‘zgartirish")
async def hr_status_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role not in (UserRole.HR, UserRole.ADMIN):
        await message.answer("❌ Ruxsat yo‘q.")
        return

    await state.set_state(HrEmployeeStatusFlow.enter_fx)
    await message.answer("FX ID ni kiriting (FX12345):")


@router.message(HrEmployeeStatusFlow.enter_fx)
async def hr_status_fx(message: Message, state: FSMContext, actor_role: UserRole, **_):
    fx = normalize_uid(message.text or "")
    if not is_employee_uid(fx):
        await message.answer("Noto‘g‘ri format. FX12345:")
        return

    await state.update_data(fx=fx)
    await state.set_state(HrEmployeeStatusFlow.choose_status)

    await message.answer(
        f"Xodim: <b>{fx}</b>\nHolatni tanlang:",
        reply_markup=_status_inline_kb(),
        parse_mode="HTML",
    )


@router.callback_query(HrEmployeeStatusFlow.choose_status, F.data.startswith("hr_status:"))
async def hr_status_choose(call: CallbackQuery, state: FSMContext, actor_role: UserRole, **_):
    if actor_role not in (UserRole.HR, UserRole.ADMIN):
        await call.answer("Ruxsat yo‘q", show_alert=True)
        return

    action = (call.data or "").split(":", 1)[1]

    if action == "cancel":
        await state.clear()
        if call.message:
            await call.message.edit_text("Bekor qilindi.")
        await call.answer()
        return

    if action not in ("active", "inactive"):
        await call.answer("Noto‘g‘ri tanlov", show_alert=True)
        return

    data = await state.get_data()
    fx = data.get("fx")
    if not fx:
        await state.clear()
        await call.answer("Sessiya topilmadi. Qaytadan urinib ko‘ring.", show_alert=True)
        return

    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        repo = EmployeeRepository(session)
        ok = await repo.set_status_by_uid(employee_uid=fx, status=action)
        await session.commit()

    await state.clear()

    if call.message:
        if ok:
            await call.message.edit_text(f"✅ <b>{fx}</b> status: <b>{action}</b>", parse_mode="HTML")
            await call.message.answer("HR menyu:", reply_markup=hr_menu_kb())
        else:
            await call.message.edit_text("❌ Xodim topilmadi.")
            await call.message.answer("HR menyu:", reply_markup=hr_menu_kb())

    await call.answer("Saqlandi ✅" if ok else "Topilmadi ❌", show_alert=False)


@router.message(F.text == "🔐 Parol tiklash")
async def hr_reset_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role not in (UserRole.HR, UserRole.ADMIN):
        await message.answer("❌ Ruxsat yo‘q.")
        return

    await state.set_state(HrResetPasswordFlow.enter_fx)
    await message.answer("FX ID ni kiriting (FX12345):")


@router.message(HrResetPasswordFlow.enter_fx)
async def hr_reset_fx(message: Message, state: FSMContext, actor_role: UserRole, **_):
    fx = normalize_uid(message.text or "")
    if not is_employee_uid(fx):
        await message.answer("Noto‘g‘ri format. FX12345:")
        return

    await state.update_data(fx=fx)
    await state.set_state(HrResetPasswordFlow.confirm)
    await message.answer("Tasdiqlash uchun 'YES' deb yozing:")


@router.message(HrResetPasswordFlow.confirm)
async def hr_reset_confirm(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if (message.text or "").strip().upper() != "YES":
        await message.answer("Bekor qilindi.", reply_markup=hr_menu_kb())
        await state.clear()
        return

    data = await state.get_data()
    fx = data["fx"]

    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.services.credential_service import CredentialService
        svc = CredentialService(session=session)
        new_pass = await svc.reset_employee_password(employee_uid=fx)
        await session.commit()

    if new_pass:
        await message.answer(f"✅ Yangi parol: <code>{new_pass}</code>", reply_markup=hr_menu_kb())
    else:
        await message.answer("❌ Xodim topilmadi.", reply_markup=hr_menu_kb())
    await state.clear()
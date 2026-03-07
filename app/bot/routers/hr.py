from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.hr import hr_menu_kb, hr_status_inline_kb
from app.bot.keyboards.common import paginated_inline_kb, tx, yes_no_kb
from app.bot.states.hr import HrEmployeeStatusFlow, HrResetPasswordFlow
from app.core.logging import get_logger
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


def _allowed(role: UserRole) -> bool:
    return role in (UserRole.HR, UserRole.ADMIN)


async def _employee_items(session, query: str | None = None, pick_prefix: str = "pick_emp"):

    from app.repositories.employees import EmployeeRepository
    repo = EmployeeRepository(session)
    rows = await (repo.search(query, limit=100) if query else repo.list(limit=100))
    return [(f"{e.full_name} · {e.employee_uid}", f"{pick_prefix}:{e.employee_uid}") for e in rows]


@router.message(F.text.in_({"👥 Xodimlar", tx("menu.hr.employees")}))
async def hr_list(message: Message, actor_role: UserRole, **_):
    if not _allowed(actor_role):
        await message.answer(tx("common.no_access"))
        return
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, pick_prefix="pick_emp")
    if not items:
        await message.answer(tx("list.empty"), reply_markup=hr_menu_kb())
        return
    await message.answer(
        "👥 Xodimlar ro‘yxati:",
        reply_markup=paginated_inline_kb(items, nav_prefix="hr_list", lang="uz", add_search=True),
    )


@router.callback_query(F.data.startswith("hr_list:page:"))
async def hr_list_page(call: CallbackQuery):
    page = int((call.data or "0").split(":")[-1])
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session)
    await call.message.edit_reply_markup(reply_markup=paginated_inline_kb(items, page=page, nav_prefix="hr_list", lang="uz", add_search=True))
    await call.answer()


@router.callback_query(F.data == "hr_list:search")
async def hr_list_search_hint(call: CallbackQuery):
    await call.answer()
    await call.message.answer("HR bo‘limida qidiruv uchun ‘Holatni o‘zgartirish’ yoki ‘Parol tiklash’ bo‘limidan foydalaning.")


@router.message(F.text.in_({"🔁 Holatni o‘zgartirish", tx("menu.hr.status")}))
async def hr_status_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if not _allowed(actor_role):
        await message.answer(tx("common.no_access"))
        return
    await state.set_state(HrEmployeeStatusFlow.choose_employee)
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, pick_prefix="pick_emp")
    await message.answer(tx("flow.choose_employee"), reply_markup=paginated_inline_kb(items, nav_prefix="hr_status", lang="uz", add_search=True))


@router.callback_query(HrEmployeeStatusFlow.choose_employee, F.data.startswith("hr_status:page:"))
async def hr_status_page(call: CallbackQuery, state: FSMContext):
    page = int((call.data or "0").split(":")[-1])
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, pick_prefix="pick_emp")
    await call.message.edit_reply_markup(reply_markup=paginated_inline_kb(items, page=page, nav_prefix="hr_status", lang="uz", add_search=True))
    await call.answer()


@router.callback_query(HrEmployeeStatusFlow.choose_employee, F.data == "hr_status:search")
async def hr_status_search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(HrEmployeeStatusFlow.search_employee)
    await call.message.answer(tx("list.search_prompt"))
    await call.answer()


@router.message(HrEmployeeStatusFlow.search_employee)
async def hr_status_search_run(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, query=query, pick_prefix="pick_emp")
    if not items:
        await message.answer(tx("list.empty"))
        return
    await state.set_state(HrEmployeeStatusFlow.choose_employee)
    await message.answer(tx("list.search_results"), reply_markup=paginated_inline_kb(items, nav_prefix="hr_status", lang="uz", add_search=True))


@router.callback_query(HrEmployeeStatusFlow.choose_employee, F.data.startswith("pick_emp:"))
async def hr_status_pick(call: CallbackQuery, state: FSMContext):
    fx = (call.data or "").split(":", 1)[1]
    await state.update_data(fx=fx)
    await state.set_state(HrEmployeeStatusFlow.choose_status)
    await call.message.answer(f"Xodim: <b>{fx}</b>\nHolatni tanlang:", reply_markup=hr_status_inline_kb(lang="uz"), parse_mode="HTML")
    await call.answer()


@router.callback_query(HrEmployeeStatusFlow.choose_status, F.data.startswith("hr_status:"))
async def hr_status_choose(call: CallbackQuery, state: FSMContext, actor_role: UserRole, **_):
    if not _allowed(actor_role):
        await call.answer("Ruxsat yo‘q", show_alert=True)
        return
    action = (call.data or "").split(":", 1)[1]
    if action == "cancel":
        await state.clear()
        await call.message.answer(tx("menu.hr.title"), reply_markup=hr_menu_kb())
        await call.answer()
        return
    data = await state.get_data()
    fx = data.get("fx")
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        repo = EmployeeRepository(session)
        ok = await repo.set_status_by_uid(employee_uid=fx, status=action)
        await session.commit()
    await state.clear()
    await call.message.answer("✅ Saqlandi." if ok else "❌ Xodim topilmadi.", reply_markup=hr_menu_kb())
    await call.answer()


@router.message(F.text.in_({"🔐 Parol tiklash", tx("menu.hr.reset")}))
async def hr_reset_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if not _allowed(actor_role):
        await message.answer(tx("common.no_access"))
        return
    await state.set_state(HrResetPasswordFlow.choose_employee)
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, pick_prefix="pick_reset")
    await message.answer(tx("flow.choose_employee"), reply_markup=paginated_inline_kb(items, nav_prefix="hr_reset", lang="uz", add_search=True))


@router.callback_query(HrResetPasswordFlow.choose_employee, F.data.startswith("hr_reset:page:"))
async def hr_reset_page(call: CallbackQuery, state: FSMContext):
    page = int((call.data or "0").split(":")[-1])
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, pick_prefix="pick_reset")
    await call.message.edit_reply_markup(reply_markup=paginated_inline_kb(items, page=page, nav_prefix="hr_reset", lang="uz", add_search=True))
    await call.answer()


@router.callback_query(HrResetPasswordFlow.choose_employee, F.data == "hr_reset:search")
async def hr_reset_search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(HrResetPasswordFlow.search_employee)
    await call.message.answer(tx("list.search_prompt"))
    await call.answer()


@router.message(HrResetPasswordFlow.search_employee)
async def hr_reset_search_run(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        items = await _employee_items(session, query=query, pick_prefix="pick_reset")
    if not items:
        await message.answer(tx("list.empty"))
        return
    await state.set_state(HrResetPasswordFlow.choose_employee)
    await message.answer(tx("list.search_results"), reply_markup=paginated_inline_kb(items, nav_prefix="hr_reset", lang="uz", add_search=True))


@router.callback_query(HrResetPasswordFlow.choose_employee, F.data.startswith("pick_reset:"))
async def hr_reset_pick(call: CallbackQuery, state: FSMContext):
    fx = (call.data or "").split(":", 1)[1]
    await state.update_data(fx=fx)
    await state.set_state(HrResetPasswordFlow.confirm)
    await call.message.answer(f"<b>{fx}</b> uchun parolni tiklaysizmi?", reply_markup=yes_no_kb(lang="uz"), parse_mode="HTML")
    await call.answer()


@router.message(HrResetPasswordFlow.confirm)
async def hr_reset_confirm(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if (message.text or "").strip() != tx("common.yes"):
        await message.answer(tx("common.cancelled"), reply_markup=hr_menu_kb())
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
    await state.clear()
    await message.answer(f"✅ Yangi parol: <code>{new_pass}</code>" if new_pass else "❌ Xodim topilmadi.", reply_markup=hr_menu_kb())

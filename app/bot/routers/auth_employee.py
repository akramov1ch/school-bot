from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.states.auth import EmployeeLogin
from app.bot.keyboards.start import start_kb
from app.bot.keyboards.teacher import teacher_menu_kb
from app.bot.keyboards.cashier import cashier_menu_kb
from app.bot.keyboards.hr import hr_menu_kb
from app.bot.keyboards.admin import admin_menu_kb
from app.bot.keyboards.common import action_kb, tx
from app.core.logging import get_logger
from app.core.utils import is_employee_uid, normalize_uid
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


@router.message(F.text.in_({"🧑‍💼 Xodim sifatida kirish", tx("start.employee_login")}))
async def employee_entry(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.GUEST:
        await message.answer("Siz allaqachon tizimdasiz. /start bosing.")
        return
    await state.set_state(EmployeeLogin.waiting_fx)
    await message.answer("FX ID ni kiriting (misol: FX12345):", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


@router.message(EmployeeLogin.waiting_fx)
async def employee_wait_fx(message: Message, state: FSMContext, **_):
    fx = normalize_uid(message.text or "")
    if not is_employee_uid(fx):
        await message.answer("Noto‘g‘ri format. FX12345 ko‘rinishida kiriting:")
        return
    await state.update_data(fx=fx)
    await state.set_state(EmployeeLogin.waiting_password)
    await message.answer("Parolni kiriting:", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


@router.message(EmployeeLogin.waiting_password)
async def employee_wait_password(message: Message, state: FSMContext, **_):
    data = await state.get_data()
    fx = data.get("fx")
    password = (message.text or "").strip()
    if not fx or not password:
        await message.answer("Xatolik. Qaytadan /start bosing.")
        await state.clear()
        await message.answer("Kirish turini tanlang:", reply_markup=start_kb("uz"))
        return

    from app.core.db import get_sessionmaker
    from app.core.redis import init_redis
    from app.core.config import Settings

    settings = Settings()
    redis = await init_redis(settings)
    try:
        async with get_sessionmaker()() as session:
            from app.repositories.employees import EmployeeRepository
            from app.repositories.users import UserRepository
            from app.core.cache import BruteForceProtector
            from app.core.security import verify_password

            emp_repo = EmployeeRepository(session)
            user_repo = UserRepository(session)
            bf = BruteForceProtector(redis=redis, settings=settings)

            if await bf.is_blocked("employee", fx):
                await message.answer("❌ Juda ko‘p xato urinish. 10 daqiqa kuting.")
                await state.clear()
                return

            emp = await emp_repo.get_by_employee_uid(fx)
            if not emp or emp.status != "active":
                await bf.register_failure("employee", fx)
                await message.answer("❌ FX yoki parol noto‘g‘ri.")
                return

            if not verify_password(emp.password_hash, password):
                await bf.register_failure("employee", fx)
                await message.answer("❌ FX yoki parol noto‘g‘ri.")
                return

            await bf.clear_failures("employee", fx)

            tg = message.from_user
            full_name = (tg.full_name if tg else "") or emp.full_name
            user = await user_repo.bind_employee_user(
                telegram_id=message.from_user.id,
                full_name=full_name,
                employee_id=emp.id,
                role=emp.role,
            )
            await session.commit()

        await state.clear()

        if user.role == UserRole.TEACHER:
            await message.answer("✅ Kirish muvaffaqiyatli.", reply_markup=teacher_menu_kb("uz"))
        elif user.role == UserRole.CASHIER:
            await message.answer("✅ Kirish muvaffaqiyatli.", reply_markup=cashier_menu_kb("uz"))
        elif user.role == UserRole.HR:
            await message.answer("✅ Kirish muvaffaqiyatli.", reply_markup=hr_menu_kb("uz"))
        elif user.role == UserRole.ADMIN:
            await message.answer("✅ Kirish muvaffaqiyatli.", reply_markup=admin_menu_kb("uz"))
        else:
            await message.answer("✅ Kirish muvaffaqiyatli. /start", reply_markup=None)
    finally:
        await redis.close()
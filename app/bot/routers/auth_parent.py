from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.states.auth import ParentLogin
from app.bot.keyboards.start import start_kb
from app.bot.keyboards.parent import parent_menu_kb
from app.bot.keyboards.common import action_kb, tx
from app.core.logging import get_logger
from app.core.utils import is_student_uid, normalize_uid
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


@router.message(F.text.in_({"👨‍👩‍👧 Ota-ona sifatida kirish", tx("start.parent_login")}))
async def parent_entry(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.GUEST:
        await message.answer("Siz allaqachon tizimdasiz. /start bosing.")
        return
    await state.set_state(ParentLogin.waiting_fm)
    await message.answer("FM ID ni kiriting (misol: FM12345):", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


@router.message(ParentLogin.waiting_fm)
async def parent_wait_fm(message: Message, state: FSMContext, **_):
    fm = normalize_uid(message.text or "")
    if not is_student_uid(fm):
        await message.answer("Noto‘g‘ri format. FM12345 ko‘rinishida kiriting:")
        return
    await state.update_data(fm=fm)
    await state.set_state(ParentLogin.waiting_password)
    await message.answer("Parolni kiriting:", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


@router.message(ParentLogin.waiting_password)
async def parent_wait_password(message: Message, state: FSMContext, **_):
    data = await state.get_data()
    fm = data.get("fm")
    password = (message.text or "").strip()
    if not fm or not password:
        await message.answer("Xatolik. Qaytadan /start bosing.")
        await state.clear()
        await message.answer("Kirish turini tanlang:", reply_markup=start_kb("uz"))
        return

    # Bind flow: creates/gets parent user + links to student (FM+password)
    from app.core.db import get_sessionmaker
    from app.core.redis import init_redis
    from app.core.config import Settings

    settings = Settings()
    redis = await init_redis(settings)
    try:
        async with get_sessionmaker()() as session:
            from app.repositories.students import StudentRepository
            from app.repositories.users import UserRepository
            from app.repositories.parent_student import ParentStudentRepository
            from app.core.cache import BruteForceProtector
            from app.core.security import verify_password

            student_repo = StudentRepository(session)
            user_repo = UserRepository(session)
            ps_repo = ParentStudentRepository(session)

            bf = BruteForceProtector(redis=redis, settings=settings)
            if await bf.is_blocked("student", fm):
                await message.answer("❌ Juda ko‘p xato urinish. 10 daqiqa kuting.")
                await state.clear()
                return

            student = await student_repo.get_by_student_uid(fm)
            if not student or student.status != "active":
                await bf.register_failure("student", fm)
                await message.answer("❌ FM yoki parol noto‘g‘ri.")
                return

            if not verify_password(student.password_hash, password):
                await bf.register_failure("student", fm)
                await message.answer("❌ FM yoki parol noto‘g‘ri.")
                return

            await bf.clear_failures("student", fm)

            tg = message.from_user
            full_name = (tg.full_name if tg else "") or "Parent"
            parent_user = await user_repo.get_or_create_parent(telegram_id=message.from_user.id, full_name=full_name)

            await ps_repo.bind(parent_user_id=parent_user.id, student_id=student.id)
            await session.commit()

        await message.answer("✅ O‘quvchi muvaffaqiyatli qo‘shildi.", reply_markup=parent_menu_kb("uz"))
        await state.clear()
    finally:
        await redis.close()
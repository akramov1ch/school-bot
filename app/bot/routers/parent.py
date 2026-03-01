from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.parent import parent_menu_kb
from app.bot.states.parent import ParentBindStudent, ParentFeedback
from app.core.logging import get_logger
from app.core.utils import is_student_uid, normalize_uid
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


def _deny(message: Message) -> bool:
    return message.from_user is None


@router.message(F.text == "➕ O‘quvchi qo‘shish")
async def parent_add_student(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Bu bo‘lim faqat ota-onalar uchun.")
        return
    await state.set_state(ParentBindStudent.waiting_fm)
    await message.answer("FM ID ni kiriting (misol: FM12345):")


@router.message(ParentBindStudent.waiting_fm)
async def parent_bind_fm(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    fm = normalize_uid(message.text or "")
    if not is_student_uid(fm):
        await message.answer("Noto‘g‘ri format. FM12345 ko‘rinishida kiriting:")
        return
    await state.update_data(fm=fm)
    await state.set_state(ParentBindStudent.waiting_password)
    await message.answer("Parolni kiriting:")


@router.message(ParentBindStudent.waiting_password)
async def parent_bind_password(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    data = await state.get_data()
    fm = data.get("fm")
    password = (message.text or "").strip()

    from app.core.db import get_sessionmaker
    from app.core.redis import init_redis
    from app.core.config import Settings

    settings = Settings()
    redis = await init_redis(settings)
    try:
        async with get_sessionmaker()() as session:
            from app.repositories.students import StudentRepository
            from app.repositories.parent_student import ParentStudentRepository
            from app.core.cache import BruteForceProtector
            from app.core.security import verify_password

            student_repo = StudentRepository(session)
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
            await ps_repo.bind(parent_user_id=actor_user.id, student_id=student.id)
            await session.commit()

        await message.answer("✅ O‘quvchi muvaffaqiyatli qo‘shildi.", reply_markup=parent_menu_kb())
        await state.clear()
    finally:
        await redis.close()


@router.message(F.text == "👶 Farzandlarim")
async def parent_children(message: Message, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        return

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.parent_student import ParentStudentRepository

        repo = ParentStudentRepository(session)
        items = await repo.list_students_for_parent(actor_user.id)

    if not items:
        await message.answer("Sizda biriktirilgan o‘quvchilar yo‘q. '➕ O‘quvchi qo‘shish' ni bosing.")
        return

    lines = ["👶 Farzandlarim:\n"]
    for s in items:
        lines.append(f"• {s.full_name} ({s.class_name}) — {s.student_uid}")
    await message.answer("\n".join(lines))


@router.message(F.text == "📊 Natijalar")
async def parent_grades(message: Message, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        return

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.grades import GradeRepository

        repo = GradeRepository(session)
        rows = await repo.latest_for_parent(parent_user_id=actor_user.id, limit=20)

    if not rows:
        await message.answer("Hozircha baholar topilmadi.")
        return

    lines = ["📊 So‘nggi baholar:\n"]
    for g in rows:
        lines.append(f"• {g.student_name} ({g.class_name}) | {g.subject_name}: {g.score} | {g.date}")
    await message.answer("\n".join(lines))


@router.message(F.text == "✍️ Uyga vazifalar")
async def parent_homeworks(message: Message, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        return

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.homeworks import HomeworkRepository

        repo = HomeworkRepository(session)
        rows = await repo.latest_for_parent(parent_user_id=actor_user.id, limit=20)

    if not rows:
        await message.answer("Hozircha uyga vazifalar topilmadi.")
        return

    lines = ["✍️ So‘nggi uyga vazifalar:\n"]
    for hw in rows:
        deadline = hw.deadline or "-"
        lines.append(f"• {hw.class_name} | {hw.subject_name}\n  📝 {hw.text}\n  ⏳ {deadline}\n")
    await message.answer("\n".join(lines))


@router.message(F.text == "💳 To‘lovlar tarixi")
async def parent_payments(message: Message, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        return

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.payments import PaymentRepository

        repo = PaymentRepository(session)
        rows = await repo.latest_for_parent(parent_user_id=actor_user.id, limit=20)

    if not rows:
        await message.answer("Hozircha to‘lovlar topilmadi.")
        return

    lines = ["💳 So‘nggi to‘lovlar:\n"]
    for p in rows:
        lines.append(f"• {p.student_name} | {p.amount} {p.currency} | {p.payment_code} | {p.paid_at}")
    await message.answer("\n".join(lines))


@router.message(F.text == "📝 Taklif/Shikoyat")
async def parent_feedback_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        return
    await state.set_state(ParentFeedback.waiting_type)
    await message.answer("Turini tanlang: SUGGESTION yoki COMPLAINT (matn bilan yuboring).")


@router.message(ParentFeedback.waiting_type)
async def parent_feedback_type(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    t = (message.text or "").strip().upper()
    if t not in ("SUGGESTION", "COMPLAINT"):
        await message.answer("Noto‘g‘ri. 'SUGGESTION' yoki 'COMPLAINT' deb yozing.")
        return
    await state.update_data(type=t)
    await state.set_state(ParentFeedback.waiting_text)
    await message.answer("Matnni kiriting:")


@router.message(ParentFeedback.waiting_text)
async def parent_feedback_text(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    data = await state.get_data()
    t = data.get("type")
    text = (message.text or "").strip()
    if not text:
        await message.answer("Bo‘sh bo‘lmasin. Matnni kiriting:")
        return

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.feedback import FeedbackRepository

        repo = FeedbackRepository(session)
        await repo.create(from_parent_user_id=actor_user.id, type_=t, text=text)
        await session.commit()

    await message.answer("✅ Yuborildi.", reply_markup=parent_menu_kb())
    await state.clear()
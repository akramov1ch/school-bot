from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.parent import parent_menu_kb
from app.bot.keyboards.common import action_kb, paginated_inline_kb, tx
from app.bot.states.parent import ParentBindStudent, ParentFeedback
from app.core.logging import get_logger
from app.core.utils import is_student_uid, normalize_uid
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


def _deny(message: Message) -> bool:
    return message.from_user is None


@router.message(F.text.in_({"➕ O‘quvchi qo‘shish", tx("menu.parent.add_child")}))
async def parent_add_student(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Bu bo‘lim faqat ota-onalar uchun.")
        return
    await state.set_state(ParentBindStudent.waiting_fm)
    await message.answer("FM ID ni kiriting (misol: FM12345):", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


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
    await message.answer("Parolni kiriting:", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


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

        await message.answer("✅ O‘quvchi muvaffaqiyatli qo‘shildi.", reply_markup=parent_menu_kb("uz"))
        await state.clear()
    finally:
        await redis.close()


@router.message(F.text.in_({"👶 Farzandlarim", tx("menu.parent.children")}))
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


@router.message(F.text.in_({"📊 Natijalar", tx("menu.parent.grades")}))
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


@router.message(F.text.in_({"✍️ Uyga vazifalar", tx("menu.parent.homeworks")}))
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


@router.message(F.text.in_({"💳 To‘lovlar tarixi", tx("menu.parent.payments")}))
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


@router.message(F.text.in_({"📝 Taklif va shikoyat", tx("menu.parent.feedback")}))
async def parent_feedback_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        return
    await state.set_state(ParentFeedback.waiting_type)
    await message.answer("Murojaat turini tanlang:", reply_markup=action_kb([["💡 Taklif", "⚠️ Shikoyat"]], with_cancel=True, with_home=True))


@router.message(ParentFeedback.waiting_type)
async def parent_feedback_type(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.PARENT:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    raw = (message.text or "").strip()
    mapping = {
        "💡 Taklif": "SUGGESTION",
        "⚠️ Shikoyat": "COMPLAINT",
        "SUGGESTION": "SUGGESTION",
        "COMPLAINT": "COMPLAINT",
    }
    t = mapping.get(raw, raw.upper())
    if t not in ("SUGGESTION", "COMPLAINT"):
        await message.answer("Quyidagi tugmalardan birini tanlang: 💡 Taklif yoki ⚠️ Shikoyat")
        return
    await state.update_data(type=t)
    await state.set_state(ParentFeedback.waiting_text)
    await message.answer("Murojaat matnini kiriting:", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


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

    await message.answer("✅ Yuborildi.", reply_markup=parent_menu_kb("uz"))
    await state.clear()

@router.callback_query(F.data.startswith("parent_children:page:"))
async def parent_children_page(callback: CallbackQuery, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    page = int((callback.data or "0").split(":")[-1])
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.parent_student import ParentStudentRepository
        items = await ParentStudentRepository(session).list_students_for_parent(actor_user.id)
    buttons = [(f"{s.full_name} · {s.class_name}", f"parent_child:{s.student_uid}") for s in items]
    await callback.message.edit_reply_markup(reply_markup=paginated_inline_kb(buttons, page=page, nav_prefix="parent_children", lang="uz"))
    await callback.answer()


@router.callback_query(F.data.startswith("parent_child:"))
async def parent_child_detail(callback: CallbackQuery, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.PARENT:
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    uid = (callback.data or "").split(":", 1)[1]
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.students import StudentRepository
        student = await StudentRepository(session).get_by_student_uid(uid)
    if not student:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await callback.message.answer(f"👶 <b>{student.full_name}</b>\nID: <code>{student.student_uid}</code>")
    await callback.answer()

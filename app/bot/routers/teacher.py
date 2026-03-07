from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.teacher import teacher_menu_kb
from app.bot.keyboards.common import paginated_inline_kb, inline_items, action_kb, tx
from app.bot.states.teacher import TeacherGradeFlow, TeacherHomeworkFlow, TeacherComplaintFlow
from app.core.logging import get_logger
from app.core.timezone import now_tz, to_date_str
from app.core.db import get_sessionmaker
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


def _is_teacher(role: UserRole):
    return role == UserRole.TEACHER


async def _teacher_class_items(actor_user):
    async with get_sessionmaker()() as session:
        from app.repositories.class_subjects import ClassSubjectRepository
        cs_repo = ClassSubjectRepository(session)
        classes = await cs_repo.list_for_teacher(actor_user.employee_id)
        class_names = sorted(set(cs.cls.class_name for cs in classes))
        return [(name, name) for name in class_names]


async def _student_items_by_class(class_name: str, prefix: str):
    async with get_sessionmaker()() as session:
        from app.repositories.classes import ClassRepository
        from app.repositories.students import StudentRepository
        cls = await ClassRepository(session).get_by_name(class_name)
        students = await StudentRepository(session).list_by_class(cls.id)
        return [(s.full_name, f"{prefix}:{s.student_uid}") for s in students]


@router.message(F.text.in_({"📌 Ballar", tx("menu.teacher.grades")}))
async def teacher_grades_start(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if not _is_teacher(actor_role):
        await message.answer("❌ Bu bo‘lim faqat ustozlar uchun.")
        return
    items = await _teacher_class_items(actor_user)
    if not items:
        await message.answer("❌ Sizga hali sinflar biriktirilmagan.")
        return
    await state.set_state(TeacherGradeFlow.choose_class)
    await message.answer(tx("flow.choose_class"), reply_markup=paginated_inline_kb([(x, f"grade_cls:{x}") for x, _ in items], nav_prefix="grade_cls", lang="uz"))


@router.callback_query(TeacherGradeFlow.choose_class, F.data.startswith("grade_cls:page:"))
async def teacher_grade_select_class_page(callback: CallbackQuery, state: FSMContext, actor_user):
    page = int((callback.data or "0").split(":")[-1])
    items = await _teacher_class_items(actor_user)
    await callback.message.edit_reply_markup(reply_markup=paginated_inline_kb([(x, f"grade_cls:{x}") for x, _ in items], page=page, nav_prefix="grade_cls", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherGradeFlow.choose_class, F.data.startswith("grade_cls:"))
async def teacher_grade_select_class(callback: CallbackQuery, state: FSMContext):
    class_name = callback.data.split(":", 1)[1]
    await state.update_data(class_name=class_name)
    student_items = await _student_items_by_class(class_name, "grade_st")
    if not student_items:
        await callback.message.answer(f"❌ {class_name} sinfida o‘quvchilar topilmadi.")
        await state.clear()
        return
    await state.set_state(TeacherGradeFlow.choose_student)
    await callback.message.edit_text(f"Sinf: {class_name}\n{tx('flow.choose_student')}", reply_markup=paginated_inline_kb(student_items, nav_prefix="grade_st", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherGradeFlow.choose_student, F.data.startswith("grade_st:page:"))
async def teacher_grade_select_student_page(callback: CallbackQuery, state: FSMContext):
    page = int((callback.data or "0").split(":")[-1])
    data = await state.get_data()
    student_items = await _student_items_by_class(data["class_name"], "grade_st")
    await callback.message.edit_reply_markup(reply_markup=paginated_inline_kb(student_items, page=page, nav_prefix="grade_st", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherGradeFlow.choose_student, F.data.startswith("grade_st:"))
async def teacher_grade_select_student(callback: CallbackQuery, state: FSMContext):
    student_uid = callback.data.split(":", 1)[1]
    await state.update_data(student_uid=student_uid)
    await state.set_state(TeacherGradeFlow.enter_score)
    await callback.message.answer("⭐ Ball kiriting (0-100):", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))
    await callback.answer()


@router.message(TeacherGradeFlow.enter_score)
async def teacher_enter_score(message: Message, state: FSMContext):
    try:
        score = int((message.text or '').strip())
        if not (0 <= score <= 100):
            raise ValueError()
    except Exception:
        await message.answer("❌ Noto‘g‘ri. 0 dan 100 gacha raqam kiriting:")
        return
    await state.update_data(score=score)
    await state.set_state(TeacherGradeFlow.enter_comment)
    await message.answer("📝 Izoh yozing yoki '-' yuboring:", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


@router.message(TeacherGradeFlow.enter_comment)
async def teacher_save_grade(message: Message, state: FSMContext, actor_user):
    comment = (message.text or '').strip()
    if comment == '-':
        comment = ''
    data = await state.get_data()
    class_name = data['class_name']
    student_uid = data['student_uid']
    score = data['score']
    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        from app.repositories.students import StudentRepository
        from app.repositories.classes import ClassRepository
        from app.repositories.grades import GradeRepository
        from app.services.notifications import NotificationService
        teacher = await EmployeeRepository(session).get_by_id(actor_user.employee_id)
        student = await StudentRepository(session).get_by_student_uid(student_uid)
        cls = await ClassRepository(session).get_by_name(class_name)
        grade = await GradeRepository(session).create(
            student_id=student.id,
            class_id=cls.id,
            subject_name=teacher.subject or "Fan",
            teacher_employee_id=teacher.id,
            score=score,
            date_=to_date_str(now_tz()),
            comment=comment,
        )
        await session.commit()
        await NotificationService(session=session).notify_parents_grade(student.id, grade.id)
    await message.answer(f"✅ {student.full_name}ga {score} ball qo‘yildi.", reply_markup=teacher_menu_kb())
    await state.clear()


@router.message(F.text.in_({"✍️ Uyga vazifa", tx("menu.teacher.homework")}))
async def teacher_hw_start(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if not _is_teacher(actor_role):
        return
    items = await _teacher_class_items(actor_user)
    if not items:
        await message.answer("❌ Sinf topilmadi.")
        return
    await state.set_state(TeacherHomeworkFlow.choose_class)
    await message.answer("Qaysi sinfga vazifa berasiz?", reply_markup=paginated_inline_kb([(x, f"hw_cls:{x}") for x, _ in items], nav_prefix="hw_cls", lang="uz"))


@router.callback_query(TeacherHomeworkFlow.choose_class, F.data.startswith("hw_cls:page:"))
async def teacher_hw_select_class_page(callback: CallbackQuery, actor_user):
    page = int((callback.data or "0").split(":")[-1])
    items = await _teacher_class_items(actor_user)
    await callback.message.edit_reply_markup(reply_markup=paginated_inline_kb([(x, f"hw_cls:{x}") for x, _ in items], page=page, nav_prefix="hw_cls", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherHomeworkFlow.choose_class, F.data.startswith("hw_cls:"))
async def teacher_hw_select_class(callback: CallbackQuery, state: FSMContext):
    class_name = callback.data.split(":", 1)[1]
    await state.update_data(class_name=class_name)
    await state.set_state(TeacherHomeworkFlow.enter_text)
    await callback.message.edit_text(f"Sinf: {class_name}\n📝 Vazifa matnini yuboring:")
    await callback.answer()


@router.message(TeacherHomeworkFlow.enter_text)
async def teacher_hw_save(message: Message, state: FSMContext, actor_user):
    text = (message.text or '').strip()
    data = await state.get_data()
    class_name = data['class_name']
    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        from app.repositories.classes import ClassRepository
        from app.repositories.homeworks import HomeworkRepository
        from app.services.notifications import NotificationService
        teacher = await EmployeeRepository(session).get_by_id(actor_user.employee_id)
        cls = await ClassRepository(session).get_by_name(class_name)
        hw = await HomeworkRepository(session).create(
            class_id=cls.id,
            subject_name=teacher.subject or 'Fan',
            teacher_employee_id=teacher.id,
            text=text,
            deadline=None,
            attachment_file_id=None,
        )
        await session.commit()
        await NotificationService(session=session).notify_class_homework(cls.id, hw.id)
    await message.answer("✅ Vazifa yuborildi.", reply_markup=teacher_menu_kb())
    await state.clear()


@router.message(F.text.in_({"✉️ Shikoyat", tx("menu.teacher.complaint")}))
async def teacher_complaint_start(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if not _is_teacher(actor_role):
        return
    items = await _teacher_class_items(actor_user)
    await state.set_state(TeacherComplaintFlow.choose_class)
    await message.answer(tx("flow.choose_class"), reply_markup=paginated_inline_kb([(x, f"comp_cls:{x}") for x, _ in items], nav_prefix="comp_cls", lang="uz"))


@router.callback_query(TeacherComplaintFlow.choose_class, F.data.startswith("comp_cls:page:"))
async def teacher_comp_select_class_page(callback: CallbackQuery, actor_user):
    page = int((callback.data or "0").split(":")[-1])
    items = await _teacher_class_items(actor_user)
    await callback.message.edit_reply_markup(reply_markup=paginated_inline_kb([(x, f"comp_cls:{x}") for x, _ in items], page=page, nav_prefix="comp_cls", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherComplaintFlow.choose_class, F.data.startswith("comp_cls:"))
async def teacher_comp_select_class(callback: CallbackQuery, state: FSMContext):
    class_name = callback.data.split(":", 1)[1]
    await state.update_data(class_name=class_name)
    student_items = await _student_items_by_class(class_name, "comp_st")
    await state.set_state(TeacherComplaintFlow.choose_student)
    await callback.message.edit_text(tx("flow.choose_student"), reply_markup=paginated_inline_kb(student_items, nav_prefix="comp_st", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherComplaintFlow.choose_student, F.data.startswith("comp_st:page:"))
async def teacher_comp_select_student_page(callback: CallbackQuery, state: FSMContext):
    page = int((callback.data or "0").split(":")[-1])
    data = await state.get_data()
    student_items = await _student_items_by_class(data["class_name"], "comp_st")
    await callback.message.edit_reply_markup(reply_markup=paginated_inline_kb(student_items, page=page, nav_prefix="comp_st", lang="uz"))
    await callback.answer()


@router.callback_query(TeacherComplaintFlow.choose_student, F.data.startswith("comp_st:"))
async def teacher_comp_select_student(callback: CallbackQuery, state: FSMContext):
    await state.update_data(student_uid=callback.data.split(":", 1)[1])
    targets = [("Ota-onaga", "comp_tr:PARENT"), ("Rahbariyatga", "comp_tr:MANAGEMENT")]
    await state.set_state(TeacherComplaintFlow.choose_target)
    await callback.message.edit_text("Kimga yuborasiz?", reply_markup=inline_items(targets, lang="uz"))
    await callback.answer()


@router.callback_query(TeacherComplaintFlow.choose_target, F.data.startswith("comp_tr:"))
async def teacher_comp_select_target(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target=callback.data.split(":", 1)[1])
    await state.set_state(TeacherComplaintFlow.enter_text)
    await callback.message.answer("Shikoyat matnini yuboring:", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))
    await callback.answer()


@router.message(TeacherComplaintFlow.enter_text)
async def teacher_comp_save(message: Message, state: FSMContext, actor_user):
    text = (message.text or '').strip()
    data = await state.get_data()
    async with get_sessionmaker()() as session:
        from app.repositories.students import StudentRepository
        from app.repositories.complaints import ComplaintRepository
        from app.services.notifications import NotificationService
        student = await StudentRepository(session).get_by_student_uid(data['student_uid'])
        comp = await ComplaintRepository(session).create(
            from_teacher_employee_id=actor_user.employee_id,
            student_id=student.id,
            target_type=data['target'],
            text=text,
        )
        await session.commit()
        await NotificationService(session).notify_complaint(comp.id)
    await message.answer("✅ Shikoyat yuborildi.", reply_markup=teacher_menu_kb())
    await state.clear()

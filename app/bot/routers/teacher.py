from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.teacher import teacher_menu_kb
from app.bot.keyboards.common import dynamic_inline_kb, inline_items
from app.bot.states.teacher import TeacherGradeFlow, TeacherHomeworkFlow, TeacherComplaintFlow
from app.core.logging import get_logger
from app.core.timezone import now_tz, to_date_str
from app.core.db import get_sessionmaker
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)

# --- Yordamchi funksiya ---
def _is_teacher(role: UserRole):
    return role == UserRole.TEACHER

# ==========================================
# 📌 BALLAR (GRADING) FLOW
# ==========================================

@router.message(F.text == "📌 Ballar")
async def teacher_grades_start(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if not _is_teacher(actor_role):
        await message.answer("❌ Bu bo‘lim faqat ustozlar uchun.")
        return

    async with get_sessionmaker()() as session:
        from app.repositories.class_subjects import ClassSubjectRepository
        cs_repo = ClassSubjectRepository(session)
        # O'qituvchiga biriktirilgan sinflar ro'yxatini olish
        # (Eslatma: Repository-da list_unique_classes_for_teacher metodi bo'lishi kerak)
        classes = await cs_repo.list_for_teacher(actor_user.employee_id)
        class_names = list(set([cs.cls.class_name for cs in classes]))

    if not class_names:
        await message.answer("❌ Sizga hali sinflar biriktirilmagan.")
        return

    await state.set_state(TeacherGradeFlow.choose_class)
    await message.answer(
        "Sinfni tanlang:", 
        reply_markup=dynamic_inline_kb(class_names, "grade_cls")
    )

@router.callback_query(TeacherGradeFlow.choose_class, F.data.startswith("grade_cls:"))
async def teacher_grade_select_class(callback: CallbackQuery, state: FSMContext):
    class_name = callback.data.split(":")[1]
    await state.update_data(class_name=class_name)

    async with get_sessionmaker()() as session:
        from app.repositories.classes import ClassRepository
        from app.repositories.students import StudentRepository
        
        class_repo = ClassRepository(session)
        cls = await class_repo.get_by_name(class_name)
        
        student_repo = StudentRepository(session)
        students = await student_repo.list_by_class(cls.id)
        
        # O'quvchilar ro'yxati: [("Ism", "callback_data"), ...]
        student_items = [(s.full_name, f"grade_st:{s.student_uid}") for s in students]

    if not student_items:
        await callback.message.answer(f"❌ {class_name} sinfida o‘quvchilar topilmadi.")
        await state.clear()
        return

    await state.set_state(TeacherGradeFlow.choose_student)
    await callback.message.edit_text(
        f"Sinf: {class_name}\nO‘quvchini tanlang:",
        reply_markup=inline_items(student_items, columns=1)
    )
    await callback.answer()

@router.callback_query(TeacherGradeFlow.choose_student, F.data.startswith("grade_st:"))
async def teacher_grade_select_student(callback: CallbackQuery, state: FSMContext):
    student_uid = callback.data.split(":")[1]
    await state.update_data(student_uid=student_uid)
    
    await state.set_state(TeacherGradeFlow.enter_score)
    await callback.message.answer("⭐ Ball kiriting (0-100):")
    await callback.answer()

@router.message(TeacherGradeFlow.enter_score)
async def teacher_enter_score(message: Message, state: FSMContext):
    try:
        score = int(message.text.strip())
        if not (0 <= score <= 100): raise ValueError()
    except:
        await message.answer("❌ Noto‘g‘ri. 0 dan 100 gacha raqam kiriting:")
        return

    await state.update_data(score=score)
    await state.set_state(TeacherGradeFlow.enter_comment)
    await message.answer("📝 Izoh yozing (yoki '-' yuboring):")

@router.message(TeacherGradeFlow.enter_comment)
async def teacher_save_grade(message: Message, state: FSMContext, actor_user):
    comment = message.text.strip()
    if comment == "-": comment = ""
    
    data = await state.get_data()
    class_name = data["class_name"]
    student_uid = data["student_uid"]
    score = data["score"]

    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        from app.repositories.students import StudentRepository
        from app.repositories.classes import ClassRepository
        from app.repositories.grades import GradeRepository
        from app.services.notifications import NotificationService

        emp_repo = EmployeeRepository(session)
        teacher = await emp_repo.get_by_id(actor_user.employee_id)
        
        student_repo = StudentRepository(session)
        student = await student_repo.get_by_student_uid(student_uid)
        
        class_repo = ClassRepository(session)
        cls = await class_repo.get_by_name(class_name)

        grade_repo = GradeRepository(session)
        grade = await grade_repo.create(
            student_id=student.id,
            class_id=cls.id,
            subject_name=teacher.subject or "Fan",
            teacher_employee_id=teacher.id,
            score=score,
            date_=to_date_str(now_tz()),
            comment=comment
        )
        await session.commit()

        # Ota-onaga xabar yuborish
        notifier = NotificationService(session=session)
        await notifier.notify_parents_grade(student.id, grade.id)

    await message.answer(f"✅ {student.full_name}ga {score} ball qo‘yildi.", reply_markup=teacher_menu_kb())
    await state.clear()


# ==========================================
# ✍️ UYGA VAZIFA (HOMEWORK) FLOW
# ==========================================

@router.message(F.text == "✍️ Uyga vazifa")
async def teacher_hw_start(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if not _is_teacher(actor_role): return

    async with get_sessionmaker()() as session:
        from app.repositories.class_subjects import ClassSubjectRepository
        cs_repo = ClassSubjectRepository(session)
        classes = await cs_repo.list_for_teacher(actor_user.employee_id)
        class_names = list(set([cs.cls.class_name for cs in classes]))

    if not class_names:
        await message.answer("❌ Sinf topilmadi.")
        return

    await state.set_state(TeacherHomeworkFlow.choose_class)
    await message.answer("Qaysi sinfga vazifa berasiz?", reply_markup=dynamic_inline_kb(class_names, "hw_cls"))

@router.callback_query(TeacherHomeworkFlow.choose_class, F.data.startswith("hw_cls:"))
async def teacher_hw_select_class(callback: CallbackQuery, state: FSMContext):
    class_name = callback.data.split(":")[1]
    await state.update_data(class_name=class_name)
    
    await state.set_state(TeacherHomeworkFlow.enter_text)
    await callback.message.edit_text(f"Sinf: {class_name}\n📝 Vazifa matnini yuboring:")
    await callback.answer()

@router.message(TeacherHomeworkFlow.enter_text)
async def teacher_hw_save(message: Message, state: FSMContext, actor_user):
    text = message.text.strip()
    data = await state.get_data()
    class_name = data["class_name"]

    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        from app.repositories.classes import ClassRepository
        from app.repositories.homeworks import HomeworkRepository
        from app.services.notifications import NotificationService

        emp_repo = EmployeeRepository(session)
        teacher = await emp_repo.get_by_id(actor_user.employee_id)
        
        class_repo = ClassRepository(session)
        cls = await class_repo.get_by_name(class_name)

        hw_repo = HomeworkRepository(session)
        hw = await hw_repo.create(
            class_id=cls.id,
            subject_name=teacher.subject or "Fan",
            teacher_employee_id=teacher.id,
            text=text,
            deadline=None,
            attachment_file_id=None
        )
        await session.commit()

        notifier = NotificationService(session=session)
        await notifier.notify_class_homework(cls.id, hw.id)

    await message.answer("✅ Vazifa yuborildi.", reply_markup=teacher_menu_kb())
    await state.clear()


# ==========================================
# ✉️ SHIKOYAT (COMPLAINT) FLOW
# ==========================================

@router.message(F.text == "✉️ Shikoyat")
async def teacher_complaint_start(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if not _is_teacher(actor_role): return

    async with get_sessionmaker()() as session:
        from app.repositories.class_subjects import ClassSubjectRepository
        cs_repo = ClassSubjectRepository(session)
        classes = await cs_repo.list_for_teacher(actor_user.employee_id)
        class_names = list(set([cs.cls.class_name for cs in classes]))

    await state.set_state(TeacherComplaintFlow.choose_class)
    await message.answer("Sinfni tanlang:", reply_markup=dynamic_inline_kb(class_names, "comp_cls"))

@router.callback_query(TeacherComplaintFlow.choose_class, F.data.startswith("comp_cls:"))
async def teacher_comp_select_class(callback: CallbackQuery, state: FSMContext):
    class_name = callback.data.split(":")[1]
    await state.update_data(class_name=class_name)

    async with get_sessionmaker()() as session:
        from app.repositories.classes import ClassRepository
        from app.repositories.students import StudentRepository
        cls = await ClassRepository(session).get_by_name(class_name)
        students = await StudentRepository(session).list_by_class(cls.id)
        student_items = [(s.full_name, f"comp_st:{s.student_uid}") for s in students]

    await state.set_state(TeacherComplaintFlow.choose_student)
    await callback.message.edit_text("O‘quvchini tanlang:", reply_markup=inline_items(student_items, 1))
    await callback.answer()

@router.callback_query(TeacherComplaintFlow.choose_student, F.data.startswith("comp_st:"))
async def teacher_comp_select_student(callback: CallbackQuery, state: FSMContext):
    await state.update_data(student_uid=callback.data.split(":")[1])
    
    # Target tanlash (Parent yoki Management)
    targets = [("Ota-onaga", "comp_tr:PARENT"), ("Rahbariyatga", "comp_tr:MANAGEMENT")]
    
    await state.set_state(TeacherComplaintFlow.choose_target)
    await callback.message.edit_text("Kimga shikoyat qilmoqchisiz?", reply_markup=inline_items(targets))
    await callback.answer()

@router.callback_query(TeacherComplaintFlow.choose_target, F.data.startswith("comp_tr:"))
async def teacher_comp_select_target(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target=callback.data.split(":")[1])
    await state.set_state(TeacherComplaintFlow.enter_text)
    await callback.message.answer("Shikoyat matnini yuboring:")
    await callback.answer()

@router.message(TeacherComplaintFlow.enter_text)
async def teacher_comp_save(message: Message, state: FSMContext, actor_user):
    text = message.text.strip()
    data = await state.get_data()
    
    async with get_sessionmaker()() as session:
        from app.repositories.students import StudentRepository
        from app.repositories.complaints import ComplaintRepository
        from app.services.notifications import NotificationService

        student = await StudentRepository(session).get_by_student_uid(data["student_uid"])
        comp = await ComplaintRepository(session).create(
            from_teacher_employee_id=actor_user.employee_id,
            student_id=student.id,
            target_type=data["target"],
            text=text
        )
        await session.commit()
        await NotificationService(session).notify_complaint(comp.id)

    await message.answer("✅ Shikoyat yuborildi.", reply_markup=teacher_menu_kb())
    await state.clear()
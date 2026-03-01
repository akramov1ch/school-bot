from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.cashier import cashier_menu_kb
from app.bot.states.cashier import CashierPaymentFlow, CashierSearchPayments
from app.core.logging import get_logger
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


@router.message(F.text == "💰 To‘lov kiritish")
async def cashier_payment_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Bu bo‘lim faqat kassir uchun.")
        return
    await state.set_state(CashierPaymentFlow.choose_student)
    await message.answer("O‘quvchi FM ID ni kiriting (misol: FM12345):")


@router.message(CashierPaymentFlow.choose_student)
async def cashier_choose_student(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    student_uid = (message.text or "").strip().upper()
    await state.update_data(student_uid=student_uid)
    await state.set_state(CashierPaymentFlow.enter_amount)
    await message.answer("💰 Summa (UZS):")


@router.message(CashierPaymentFlow.enter_amount)
async def cashier_amount(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    try:
        amount = float((message.text or "").strip())
    except Exception:
        await message.answer("Noto‘g‘ri. Summa kiriting (misol: 150000):")
        return
    if amount <= 0:
        await message.answer("Musbat summa kiriting:")
        return
    await state.update_data(amount=amount)
    await state.set_state(CashierPaymentFlow.enter_method)
    await message.answer("💳 Usul (ixtiyoriy). Bo‘sh qoldirish uchun '-' yuboring:")


@router.message(CashierPaymentFlow.enter_method)
async def cashier_method(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    method = (message.text or "").strip()
    if method == "-":
        method = ""
    await state.update_data(method=method)
    await state.set_state(CashierPaymentFlow.enter_comment)
    await message.answer("📝 Izoh (ixtiyoriy). Bo‘sh qoldirish uchun '-' yuboring:")


@router.message(CashierPaymentFlow.enter_comment)
async def cashier_comment(message: Message, state: FSMContext, actor_role: UserRole, actor_user, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    comment = (message.text or "").strip()
    if comment == "-":
        comment = ""

    data = await state.get_data()
    student_uid = data["student_uid"]
    amount = float(data["amount"])
    method = data.get("method") or ""

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository
        from app.repositories.students import StudentRepository
        from app.repositories.payments import PaymentRepository
        from app.services.payment_writer import PaymentSheetWriter
        from app.services.notifications import NotificationService

        emp_repo = EmployeeRepository(session)
        cashier = await emp_repo.get_by_id(actor_user.employee_id)

        student_repo = StudentRepository(session)
        student = await student_repo.get_by_student_uid(student_uid)
        if not student:
            await message.answer("❌ O‘quvchi topilmadi.")
            await state.clear()
            return

        pay_repo = PaymentRepository(session)
        payment = await pay_repo.create_payment(
            student_id=student.id,
            amount=amount,
            currency="UZS",
            method=method or None,
            comment=comment or None,
            cashier_employee_id=cashier.id,
        )
        await session.commit()

        # Write to Sheets (async retry handled by service)
        writer = PaymentSheetWriter(session=session)
        await writer.enqueue_or_write(payment_id=payment.id)

        notifier = NotificationService(session=session)
        await notifier.notify_parents_payment(payment_id=payment.id)

    await message.answer("✅ To‘lov saqlandi va ota-onalarga yuborildi.", reply_markup=cashier_menu_kb())
    await state.clear()


@router.message(F.text == "📜 To‘lovlar qidirish")
async def cashier_search_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Bu bo‘lim faqat kassir uchun.")
        return
    await state.set_state(CashierSearchPayments.enter_query)
    await message.answer("Qidiruv: FM12345 yoki Payment ID (PAY-YYYY-000001):")


@router.message(CashierSearchPayments.enter_query)
async def cashier_search(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role != UserRole.CASHIER:
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    q = (message.text or "").strip()

    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.payments import PaymentRepository

        repo = PaymentRepository(session)
        rows = await repo.search(q=q, limit=20)

    if not rows:
        await message.answer("Topilmadi.", reply_markup=cashier_menu_kb())
        await state.clear()
        return

    lines = ["📜 Natijalar:\n"]
    for p in rows:
        lines.append(f"• {p.payment_code} | {p.student_name} | {p.amount} {p.currency} | {p.paid_at}")
    await message.answer("\n".join(lines), reply_markup=cashier_menu_kb())
    await state.clear()
from __future__ import annotations

import base64

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.states.face import FaceEnrollFlow
from app.core.logging import get_logger
from app.models.enums import UserRole
from app.bot.keyboards.common import action_kb, tx

router = Router()
logger = get_logger(__name__)


@router.message(F.text.in_({"📷 Selfie FaceID", tx("menu.teacher.faceid"), tx("menu.hr.faceid"), tx("menu.cashier.faceid"), tx("menu.admin.faceid_selfie")}))
async def face_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if actor_role not in (UserRole.TEACHER, UserRole.CASHIER, UserRole.HR, UserRole.ADMIN):
        await message.answer("❌ Bu bo‘lim faqat xodimlar uchun.")
        return
    await state.set_state(FaceEnrollFlow.waiting_selfie)
    await message.answer("📷 Selfie rasmini yuboring.", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))


@router.message(FaceEnrollFlow.waiting_selfie, F.photo)
async def face_receive(message: Message, state: FSMContext, actor_role: UserRole, actor_user, bot, **_):
    if actor_role not in (UserRole.TEACHER, UserRole.CASHIER, UserRole.HR, UserRole.ADMIN):
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    if not actor_user or not actor_user.employee_id:
        await message.answer("❌ Xodim profili topilmadi.")
        await state.clear()
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    image_bytes = file_bytes.read()

    from app.core.db import get_sessionmaker
    from app.services.attendance import FaceEnrollmentService

    async with get_sessionmaker()() as session:
        svc = FaceEnrollmentService(session=session)
        report = await svc.enroll_employee_face(employee_id=actor_user.employee_id, image_bytes=image_bytes)
        await session.commit()

    lines = ["📷 FaceID yuklash natijasi:\n"]
    for row in report:
        ok = "✅" if row["ok"] else "❌"
        lines.append(f"{ok} {row['device_ip']} ({row['device_type']}): {row.get('detail','')}")
    await message.answer("\n".join(lines))
    await state.clear()


@router.message(FaceEnrollFlow.waiting_selfie)
async def face_need_photo(message: Message, **_):
    await message.answer("Iltimos, rasm yuboring.", reply_markup=action_kb([], lang="uz", with_cancel=True, with_home=True))
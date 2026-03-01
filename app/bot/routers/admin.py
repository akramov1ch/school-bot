from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.admin import admin_menu_kb
from app.bot.states.admin import AdminManualSyncFlow, AdminCredentialResetFlow, AdminFaceIdFlow
from app.core.logging import get_logger
from app.core.utils import is_employee_uid, is_student_uid, normalize_uid
from app.models.enums import UserRole

router = Router()
logger = get_logger(__name__)


def _admin_only(actor_role: UserRole) -> bool:
    return actor_role == UserRole.ADMIN


@router.message(F.text == "🔄 Manual sync")
async def admin_manual_sync_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        return
    await state.set_state(AdminManualSyncFlow.confirm)
    await message.answer("Sync boshlansinmi? 'YES' deb yozing:")


@router.message(AdminManualSyncFlow.confirm)
async def admin_manual_sync_run(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        await state.clear()
        return
    if (message.text or "").strip().upper() != "YES":
        await message.answer("Bekor qilindi.", reply_markup=admin_menu_kb())
        await state.clear()
        return

    from app.core.db import get_sessionmaker
    from app.services.sync_sheets import SheetsSyncService

    async with get_sessionmaker()() as session:
        svc = SheetsSyncService(session=session)
        res = await svc.sync_all()
        await session.commit()

    await message.answer(f"✅ Manual sync yakunlandi: {res}", reply_markup=admin_menu_kb())
    await state.clear()


@router.message(F.text == "🔐 Credential reset")
async def admin_cred_reset_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        return
    await state.set_state(AdminCredentialResetFlow.choose_type)
    await message.answer("Tur: FM yoki FX deb yozing:")


@router.message(AdminCredentialResetFlow.choose_type)
async def admin_cred_type(message: Message, state: FSMContext, actor_role: UserRole, **_):
    t = (message.text or "").strip().upper()
    if t not in ("FM", "FX"):
        await message.answer("Noto‘g‘ri. FM yoki FX deb yozing:")
        return
    await state.update_data(type=t)
    await state.set_state(AdminCredentialResetFlow.enter_uid)
    await message.answer(f"{t} ID ni kiriting:")


@router.message(AdminCredentialResetFlow.enter_uid)
async def admin_cred_uid(message: Message, state: FSMContext, actor_role: UserRole, **_):
    data = await state.get_data()
    t = data["type"]
    uid = normalize_uid(message.text or "")

    if t == "FM" and not is_student_uid(uid):
        await message.answer("Noto‘g‘ri FM format. FM12345:")
        return
    if t == "FX" and not is_employee_uid(uid):
        await message.answer("Noto‘g‘ri FX format. FX12345:")
        return

    await state.update_data(uid=uid)
    await state.set_state(AdminCredentialResetFlow.confirm)
    await message.answer("Tasdiqlash uchun 'YES' deb yozing:")


@router.message(AdminCredentialResetFlow.confirm)
async def admin_cred_confirm(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if (message.text or "").strip().upper() != "YES":
        await message.answer("Bekor qilindi.", reply_markup=admin_menu_kb())
        await state.clear()
        return
    data = await state.get_data()
    t = data["type"]
    uid = data["uid"]

    from app.core.db import get_sessionmaker
    from app.services.credential_service import CredentialService

    async with get_sessionmaker()() as session:
        svc = CredentialService(session=session)
        if t == "FM":
            new_pass = await svc.reset_student_password(student_uid=uid)
        else:
            new_pass = await svc.reset_employee_password(employee_uid=uid)
        await session.commit()

    if new_pass:
        await message.answer(f"✅ Yangi parol: <code>{new_pass}</code>", reply_markup=admin_menu_kb())
    else:
        await message.answer("❌ Topilmadi.", reply_markup=admin_menu_kb())
    await state.clear()


@router.message(F.text == "📥 Feedback inbox")
async def admin_feedback_inbox(message: Message, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        return
    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.feedback import FeedbackRepository

        repo = FeedbackRepository(session)
        items = await repo.list_unseen(limit=20)

    if not items:
        await message.answer("Inbox bo‘sh.", reply_markup=admin_menu_kb())
        return

    lines = ["📥 Feedback inbox (top 20):\n"]
    for f in items:
        lines.append(f"• [{f.type}] {f.text} (parent_user_id={f.from_parent_user_id})")
    await message.answer("\n".join(lines), reply_markup=admin_menu_kb())


@router.message(F.text == "🕵️ Audit log")
async def admin_audit_log(message: Message, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        return
    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        from app.repositories.audit_logs import AuditLogRepository

        repo = AuditLogRepository(session)
        items = await repo.latest(limit=30)

    if not items:
        await message.answer("Audit bo‘sh.", reply_markup=admin_menu_kb())
        return

    lines = ["🕵️ Audit log (top 30):\n"]
    for a in items:
        lines.append(f"• {a.created_at} | actor={a.actor_user_id} | {a.action}")
    await message.answer("\n".join(lines), reply_markup=admin_menu_kb())


@router.message(F.text == "🧑‍🔧 FaceID admin")
async def admin_faceid_start(message: Message, state: FSMContext, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        return
    await state.set_state(AdminFaceIdFlow.choose_action)
    await message.answer("Amal: ADD_BRANCH / ADD_DEVICE / BIND_NOTIFY deb yozing:")


@router.message(AdminFaceIdFlow.choose_action)
async def admin_faceid_choose(message: Message, state: FSMContext, actor_role: UserRole, **_):
    act = (message.text or "").strip().upper()
    if act not in ("ADD_BRANCH", "ADD_DEVICE", "BIND_NOTIFY"):
        await message.answer("Noto‘g‘ri. ADD_BRANCH / ADD_DEVICE / BIND_NOTIFY:")
        return
    await state.update_data(action=act)

    if act == "ADD_BRANCH":
        await state.set_state(AdminFaceIdFlow.add_branch_name)
        await message.answer("Filial nomi:")
    elif act == "ADD_DEVICE":
        await state.set_state(AdminFaceIdFlow.add_device_branch)
        await message.answer("Filial nomi (device qaysi filialga):")
    else:
        await state.set_state(AdminFaceIdFlow.bind_notify_fx)
        await message.answer("Xodim FX ID (FX12345):")


@router.message(AdminFaceIdFlow.add_branch_name)
async def admin_faceid_branch_name(message: Message, state: FSMContext, actor_role: UserRole, **_):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Bo‘sh bo‘lmasin. Filial nomi:")
        return
    await state.update_data(branch_name=name)
    await state.set_state(AdminFaceIdFlow.add_branch_sheet)
    await message.answer("Attendance sheet ID (Google spreadsheet id):")


@router.message(AdminFaceIdFlow.add_branch_sheet)
async def admin_faceid_branch_sheet(message: Message, state: FSMContext, actor_role: UserRole, **_):
    sheet_id = (message.text or "").strip()
    data = await state.get_data()
    name = data["branch_name"]

    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.branches import BranchRepository

        repo = BranchRepository(session)
        await repo.create(name=name, attendance_sheet_id=sheet_id)
        await session.commit()

    await message.answer("✅ Filial qo‘shildi.", reply_markup=admin_menu_kb())
    await state.clear()


@router.message(AdminFaceIdFlow.add_device_branch)
async def admin_faceid_device_branch(message: Message, state: FSMContext, actor_role: UserRole, **_):
    branch_name = (message.text or "").strip()
    if not branch_name:
        await message.answer("Bo‘sh bo‘lmasin. Filial nomi:")
        return
    await state.update_data(branch_name=branch_name)
    await state.set_state(AdminFaceIdFlow.add_device_ip)
    await message.answer("IP address (misol: 192.168.1.10):")


@router.message(AdminFaceIdFlow.add_device_ip)
async def admin_faceid_device_ip(message: Message, state: FSMContext, actor_role: UserRole, **_):
    ip = (message.text or "").strip()
    await state.update_data(ip=ip)
    await state.set_state(AdminFaceIdFlow.add_device_username)
    await message.answer("Device username:")


@router.message(AdminFaceIdFlow.add_device_username)
async def admin_faceid_device_user(message: Message, state: FSMContext, actor_role: UserRole, **_):
    username = (message.text or "").strip()
    await state.update_data(username=username)
    await state.set_state(AdminFaceIdFlow.add_device_password)
    await message.answer("Device password:")


@router.message(AdminFaceIdFlow.add_device_password)
async def admin_faceid_device_pass(message: Message, state: FSMContext, actor_role: UserRole, **_):
    pwd = (message.text or "").strip()
    await state.update_data(password=pwd)
    await state.set_state(AdminFaceIdFlow.add_device_type)
    await message.answer("Device type: entry / exit / universal:")


@router.message(AdminFaceIdFlow.add_device_type)
async def admin_faceid_device_type(message: Message, state: FSMContext, actor_role: UserRole, **_):
    dtype = (message.text or "").strip().lower()
    if dtype not in ("entry", "exit", "universal"):
        await message.answer("Noto‘g‘ri. entry / exit / universal:")
        return

    data = await state.get_data()
    branch_name = data["branch_name"]
    ip = data["ip"]
    username = data["username"]
    password = data["password"]

    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.branches import BranchRepository
        from app.repositories.devices import DeviceRepository

        b_repo = BranchRepository(session)
        branch = await b_repo.get_by_name(branch_name)
        if not branch:
            await message.answer("❌ Filial topilmadi.", reply_markup=admin_menu_kb())
            await state.clear()
            return

        d_repo = DeviceRepository(session)
        await d_repo.create(branch_id=branch.id, ip_address=ip, username=username, password=password, device_type=dtype)
        await session.commit()

    await message.answer("✅ Device qo‘shildi.", reply_markup=admin_menu_kb())
    await state.clear()


@router.message(AdminFaceIdFlow.bind_notify_fx)
async def admin_faceid_bind_fx(message: Message, state: FSMContext, actor_role: UserRole, **_):
    fx = normalize_uid(message.text or "")
    if not is_employee_uid(fx):
        await message.answer("Noto‘g‘ri FX. FX12345:")
        return
    await state.update_data(fx=fx)
    await state.set_state(AdminFaceIdFlow.bind_notify_chat)
    await message.answer("Notification chat_id (raqam):")


@router.message(AdminFaceIdFlow.bind_notify_chat)
async def admin_faceid_bind_chat(message: Message, state: FSMContext, actor_role: UserRole, **_):
    try:
        chat_id = int((message.text or "").strip())
    except Exception:
        await message.answer("Noto‘g‘ri. chat_id raqam bo‘lsin:")
        return
    data = await state.get_data()
    fx = data["fx"]

    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        from app.repositories.employees import EmployeeRepository

        repo = EmployeeRepository(session)
        ok = await repo.set_notification_chat(employee_uid=fx, chat_id=chat_id)
        await session.commit()

    if ok:
        await message.answer("✅ Bog‘landi.", reply_markup=admin_menu_kb())
    else:
        await message.answer("❌ Xodim topilmadi.", reply_markup=admin_menu_kb())
    await state.clear()


@router.message(F.text == "🧩 Class-Subject-Teacher")
async def admin_mapping_info(message: Message, actor_role: UserRole, **_):
    if not _admin_only(actor_role):
        await message.answer("❌ Ruxsat yo‘q.")
        return
    await message.answer(
        "🧩 Mapping bu MVPda Sheets sync orqali yuritiladi.\n"
        "Muammolarni tekshirish uchun 'sync_logs' va 'class_subjects' jadvalini ko‘ring.",
        reply_markup=admin_menu_kb(),
    )
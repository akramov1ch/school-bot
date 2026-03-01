from aiogram.fsm.state import State, StatesGroup


class AdminManualSyncFlow(StatesGroup):
    confirm = State()


class AdminCredentialResetFlow(StatesGroup):
    choose_type = State()  # FM/FX
    enter_uid = State()
    confirm = State()


class AdminFaceIdFlow(StatesGroup):
    choose_action = State()
    add_branch_name = State()
    add_branch_sheet = State()
    add_device_branch = State()
    add_device_ip = State()
    add_device_username = State()
    add_device_password = State()
    add_device_type = State()
    bind_notify_fx = State()
    bind_notify_chat = State()
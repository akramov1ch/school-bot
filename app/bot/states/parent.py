from aiogram.fsm.state import State, StatesGroup


class ParentBindStudent(StatesGroup):
    waiting_fm = State()
    waiting_password = State()


class ParentFeedback(StatesGroup):
    waiting_type = State()
    waiting_text = State()
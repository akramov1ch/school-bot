from aiogram.fsm.state import State, StatesGroup


class ParentLogin(StatesGroup):
    waiting_fm = State()
    waiting_password = State()


class EmployeeLogin(StatesGroup):
    waiting_fx = State()
    waiting_password = State()
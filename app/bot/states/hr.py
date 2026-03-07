from aiogram.fsm.state import State, StatesGroup


class HrEmployeeStatusFlow(StatesGroup):
    choose_employee = State()
    search_employee = State()
    choose_status = State()


class HrResetPasswordFlow(StatesGroup):
    choose_employee = State()
    search_employee = State()
    confirm = State()

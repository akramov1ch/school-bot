from aiogram.fsm.state import State, StatesGroup


class HrEmployeeStatusFlow(StatesGroup):
    enter_fx = State()
    choose_status = State()


class HrResetPasswordFlow(StatesGroup):
    enter_fx = State()
    confirm = State()
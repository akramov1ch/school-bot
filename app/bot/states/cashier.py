from aiogram.fsm.state import State, StatesGroup


class CashierPaymentFlow(StatesGroup):
    choose_student = State()
    enter_amount = State()
    enter_method = State()
    enter_comment = State()
    confirm = State()


class CashierSearchPayments(StatesGroup):
    enter_query = State()
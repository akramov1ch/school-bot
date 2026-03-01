from aiogram.fsm.state import State, StatesGroup


class TeacherGradeFlow(StatesGroup):
    choose_class = State()
    choose_student = State()
    enter_score = State()
    enter_comment = State()
    enter_date = State()


class TeacherHomeworkFlow(StatesGroup):
    choose_class = State()
    enter_text = State()
    enter_deadline = State()
    upload_attachment = State()


class TeacherComplaintFlow(StatesGroup):
    choose_class = State()
    choose_student = State()
    choose_target = State()
    enter_text = State()
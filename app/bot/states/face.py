from aiogram.fsm.state import State, StatesGroup


class FaceEnrollFlow(StatesGroup):
    waiting_selfie = State()
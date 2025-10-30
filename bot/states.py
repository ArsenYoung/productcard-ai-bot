from aiogram.fsm.state import State, StatesGroup


class GenerationStates(StatesGroup):
    choosing_platform = State()
    waiting_input = State()


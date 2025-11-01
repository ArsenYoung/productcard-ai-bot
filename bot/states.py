from aiogram.fsm.state import State, StatesGroup


class GenerationStates(StatesGroup):
    choosing_platform = State()
    choosing_language = State()
    choosing_tone = State()
    choosing_length = State()
    waiting_input = State()
    generating = State()

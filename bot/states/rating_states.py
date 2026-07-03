from aiogram.fsm.state import State, StatesGroup


class RatingStates(StatesGroup):
    """FSM состояния — оценка доставки."""
    # Шаг 0: выбор оценки (1-5 звёзд)
    rating = State()
    # Шаг 1: комментарий (опционально)
    comment = State()

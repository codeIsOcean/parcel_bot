from aiogram.fsm.state import State, StatesGroup


class CreateParcelStates(StatesGroup):
    """FSM состояния — создание посылки (7 шагов)."""
    # Шаг 0: выбор города отправления
    from_city = State()
    # Шаг 1: выбор города назначения
    to_city = State()
    # Шаг 2: описание содержимого
    description = State()
    # Шаг 3: вес посылки
    weight = State()
    # Шаг 4: фото посылки (опционально)
    photo = State()
    # Шаг 5: предложить цену
    price = State()
    # Шаг 6: подтверждение
    confirm = State()

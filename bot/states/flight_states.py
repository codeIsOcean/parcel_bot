from aiogram.fsm.state import State, StatesGroup


class PublishFlightStates(StatesGroup):
    """FSM состояния — публикация рейса (6 шагов)."""
    # Шаг 0: город отправления
    from_city = State()
    # Шаг 1: город назначения
    to_city = State()
    # Шаг 2: дата вылета
    flight_date = State()
    # Шаг 3: свободный вес
    available_kg = State()
    # Шаг 4: цена за кг
    price_per_kg = State()
    # Шаг 5: подтверждение
    confirm = State()

from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    name = State()
    price = State()
    photo = State()
    waiting_for_name = State()
    waiting_for_category = State() # Yangi holat
    waiting_for_price = State()
    waiting_for_photo = State()
    waiting_for_broadcast_message = State()
    waiting_for_quantity = State()
    waiting_for_edit_quantity = State()
    quantity = State()
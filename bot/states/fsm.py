from aiogram.fsm.state import State, StatesGroup


class AddChildFSM(StatesGroup):
    """FSM добавления ребёнка."""
    input_name = State()
    input_age = State()
    select_emoji = State()
    input_telegram_id = State()


class AddLocationFSM(StatesGroup):
    """FSM добавления нового места занятий."""
    input_name = State()
    input_address = State()
    input_note = State()


class AddActivityFSM(StatesGroup):
    """FSM добавления нового занятия."""
    select_child = State()
    select_category = State()
    input_title = State()
    select_schedule_type = State()
    select_days = State()
    input_date = State()
    input_start_time = State()
    input_end_time = State()
    select_location = State()
    input_new_location_name = State()
    input_new_location_address = State()
    input_teacher = State()
    input_items = State()
    input_notes = State()
    confirm = State()


class EditActivityFSM(StatesGroup):
    """FSM редактирования занятия."""
    select_field = State()
    input_new_value = State()


class UserSettingsFSM(StatesGroup):
    """FSM изменения настроек пользователя."""
    select_timezone = State()
    input_custom_timezone = State()
    input_quiet_hours = State()
    input_digest_time = State()

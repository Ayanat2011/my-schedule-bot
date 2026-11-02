from bot.handlers.common import router as common_router
from bot.handlers.schedule import router as schedule_router
from bot.handlers.add_activity import router as add_activity_router
from bot.handlers.manage_activity import router as manage_activity_router
from bot.handlers.children import router as children_router
from bot.handlers.locations import router as locations_router
from bot.handlers.reminders import router as reminders_router
from bot.handlers.settings import router as settings_router
from bot.handlers.admin import router as admin_router

__all__ = [
    "common_router",
    "schedule_router",
    "add_activity_router",
    "manage_activity_router",
    "children_router",
    "locations_router",
    "reminders_router",
    "settings_router",
    "admin_router",
]

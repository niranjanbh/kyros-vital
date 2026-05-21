from app.wellness.routes.lab_reports import router as lab_reports_router
from app.wellness.routes.logs import router as logs_router
from app.wellness.routes.measurements import router as measurements_router
from app.wellness.routes.reminders import router as reminders_router
from app.wellness.routes.tracked_items import router as tracked_items_router

__all__ = [
    "tracked_items_router",
    "reminders_router",
    "logs_router",
    "measurements_router",
    "lab_reports_router",
]

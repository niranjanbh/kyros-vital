from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.admin.routes.audit import router as audit_router
from app.admin.routes.consultations import router as consultations_router
from app.admin.routes.dashboard import router as dashboard_router
from app.admin.routes.health import router as health_router
from app.admin.routes.items import router as items_router
from app.admin.routes.reminders import router as reminders_router
from app.admin.routes.users import router as users_router

admin_router = APIRouter(prefix="/admin", default_response_class=HTMLResponse)
admin_router.include_router(dashboard_router)
admin_router.include_router(users_router)
admin_router.include_router(items_router)
admin_router.include_router(reminders_router)
admin_router.include_router(consultations_router)
admin_router.include_router(audit_router)
admin_router.include_router(health_router)

__all__ = ["admin_router"]

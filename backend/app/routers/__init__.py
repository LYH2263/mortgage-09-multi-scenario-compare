from fastapi import APIRouter
from app.routers import compare, dashboard, history, loans, schedule, settings
api = APIRouter(prefix="/api")
for r in (dashboard, loans, schedule, compare, history, settings): api.include_router(r.router)

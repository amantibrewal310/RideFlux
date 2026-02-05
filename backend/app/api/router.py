from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.rides import router as rides_router
from app.api.drivers import router as drivers_router
from app.api.trips import router as trips_router
from app.api.payments import router as payments_router

api_router = APIRouter()

# Health check at root level
api_router.include_router(health_router)

# Versioned API routes
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(rides_router)
v1_router.include_router(drivers_router)
v1_router.include_router(trips_router)
v1_router.include_router(payments_router)

api_router.include_router(v1_router)

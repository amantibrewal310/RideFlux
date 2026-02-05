import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.middleware import IdempotencyMiddleware, RateLimiterMiddleware, register_exception_handlers
from app.database import async_session
from app.redis_client import close_redis, get_redis, init_redis
from app.services.matching_service import poll_expired_offers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    # Start background task for expired offer polling
    task = asyncio.create_task(poll_expired_offers(async_session, get_redis()))
    yield
    task.cancel()
    await close_redis()


app = FastAPI(title="RideFlux", version="1.0.0", lifespan=lifespan)

# Middleware (order matters: outermost first)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Routes
from app.api.router import api_router  # noqa: E402
from app.ws.handlers import ws_router  # noqa: E402

app.include_router(api_router)
app.include_router(ws_router)

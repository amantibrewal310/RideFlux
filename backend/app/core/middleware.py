import json
import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.exceptions import (
    DriverNotFoundError,
    DriverUnavailableError,
    DuplicateRequestError,
    InvalidStateTransitionError,
    PaymentError,
    RateLimitExceededError,
    RideFluxError,
    RideNotFoundError,
    TripNotFoundError,
)
from app.redis_client import get_redis

# ---------------------------------------------------------------------------
# Rate Limiter Middleware - sliding window, 100 requests / minute per IP
# ---------------------------------------------------------------------------

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 100


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter.

    Tracks requests per client IP using a Redis sorted set with timestamps
    as scores. Expired entries are pruned on each request.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            redis = get_redis()
        except RuntimeError:
            # Redis not available -- let request through
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        pipe = redis.pipeline()
        # Remove entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count remaining entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {f"{now}": now})
        # Set expiry on the key so it auto-cleans
        pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)
        results = await pipe.execute()

        request_count = results[1]

        if request_count >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        response = await call_next(request)
        return response


# ---------------------------------------------------------------------------
# Idempotency Middleware - caches POST responses by Idempotency-Key header
# ---------------------------------------------------------------------------

IDEMPOTENCY_TTL_SECONDS = 3600  # 1 hour


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Idempotency middleware for POST requests.

    When a POST request includes an ``Idempotency-Key`` header, the middleware
    checks Redis for a cached response. If found, the cached response is
    returned immediately. Otherwise the request is processed normally and
    the response is cached in Redis for future duplicate requests.

    Redis key format: ``idemp:{key}:{path}``
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method != "POST":
            return await call_next(request)

        idemp_key = request.headers.get("Idempotency-Key")
        if not idemp_key:
            return await call_next(request)

        try:
            redis = get_redis()
        except RuntimeError:
            return await call_next(request)

        cache_key = f"idemp:{idemp_key}:{request.url.path}"

        # Check for cached response
        cached = await redis.get(cache_key)
        if cached is not None:
            cached_data = json.loads(cached)
            return JSONResponse(
                status_code=cached_data["status_code"],
                content=cached_data["body"],
                headers={"X-Idempotent-Replay": "true"},
            )

        # Process the request
        response = await call_next(request)

        # Only cache successful responses (2xx)
        if 200 <= response.status_code < 300:
            # Read the response body
            body_bytes = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    body_bytes += chunk.encode("utf-8")
                else:
                    body_bytes += chunk

            try:
                body_json = json.loads(body_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Non-JSON response -- return as-is without caching
                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            cache_value = json.dumps(
                {"status_code": response.status_code, "body": body_json}
            )
            await redis.set(cache_key, cache_value, ex=IDEMPOTENCY_TTL_SECONDS)

            # Reconstruct the response since we consumed the body iterator
            return JSONResponse(
                status_code=response.status_code,
                content=body_json,
            )

        return response


# ---------------------------------------------------------------------------
# Exception handlers for RideFluxError subclasses
# ---------------------------------------------------------------------------

_EXCEPTION_STATUS_MAP: dict[type[RideFluxError], int] = {
    RideNotFoundError: 404,
    DriverNotFoundError: 404,
    TripNotFoundError: 404,
    DriverUnavailableError: 409,
    InvalidStateTransitionError: 409,
    DuplicateRequestError: 409,
    PaymentError: 402,
    RateLimitExceededError: 429,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Register FastAPI exception handlers for all RideFluxError subclasses."""

    @app.exception_handler(RideFluxError)
    async def rideflux_error_handler(request: Request, exc: RideFluxError) -> JSONResponse:
        status_code = _EXCEPTION_STATUS_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message},
        )

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://rideflux:rideflux_secret@localhost:5432/rideflux"
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"

    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Matching
    MATCH_RADIUS_INITIAL_KM: float = 2.0
    MATCH_RADIUS_EXPANDED_KM: float = 5.0
    OFFER_TTL_SECONDS: int = 20
    MAX_OFFERS_PER_RIDE: int = 3

    # Surge
    SURGE_MAX_MULTIPLIER: float = 3.0
    SURGE_RECOMPUTE_INTERVAL_S: int = 60

    # New Relic
    NEW_RELIC_LICENSE_KEY: str = ""
    NEW_RELIC_APP_NAME: str = "RideFlux"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

class RideFluxError(Exception):
    """Base exception for all RideFlux application errors."""

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class InvalidStateTransitionError(RideFluxError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current_state: str, target_state: str) -> None:
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(
            f"Invalid state transition from '{current_state}' to '{target_state}'"
        )


class RideNotFoundError(RideFluxError):
    """Raised when a ride request cannot be found."""

    def __init__(self, ride_id: str | None = None) -> None:
        message = f"Ride not found: {ride_id}" if ride_id else "Ride not found"
        super().__init__(message)


class DriverNotFoundError(RideFluxError):
    """Raised when a driver cannot be found."""

    def __init__(self, driver_id: str | None = None) -> None:
        message = f"Driver not found: {driver_id}" if driver_id else "Driver not found"
        super().__init__(message)


class TripNotFoundError(RideFluxError):
    """Raised when a trip cannot be found."""

    def __init__(self, trip_id: str | None = None) -> None:
        message = f"Trip not found: {trip_id}" if trip_id else "Trip not found"
        super().__init__(message)


class DriverUnavailableError(RideFluxError):
    """Raised when a driver is not available to accept rides."""

    def __init__(self, driver_id: str | None = None) -> None:
        message = (
            f"Driver unavailable: {driver_id}" if driver_id else "Driver unavailable"
        )
        super().__init__(message)


class DuplicateRequestError(RideFluxError):
    """Raised when a duplicate request is detected via idempotency key."""

    def __init__(self, idempotency_key: str | None = None) -> None:
        message = (
            f"Duplicate request detected for idempotency key: {idempotency_key}"
            if idempotency_key
            else "Duplicate request detected"
        )
        super().__init__(message)


class PaymentError(RideFluxError):
    """Raised when a payment processing error occurs."""

    def __init__(self, message: str = "Payment processing failed") -> None:
        super().__init__(message)


class RateLimitExceededError(RideFluxError):
    """Raised when a client exceeds the rate limit."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later.") -> None:
        super().__init__(message)

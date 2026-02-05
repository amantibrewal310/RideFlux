from decimal import Decimal, ROUND_HALF_UP

FARE_CONFIG: dict[str, dict[str, float]] = {
    "auto":  {"base": 25, "per_km": 8,  "per_min": 1.0, "min_fare": 30},
    "mini":  {"base": 40, "per_km": 10, "per_min": 1.5, "min_fare": 50},
    "sedan": {"base": 60, "per_km": 14, "per_min": 2.0, "min_fare": 80},
    "suv":   {"base": 80, "per_km": 18, "per_min": 2.5, "min_fare": 100},
}


def calculate_fare(
    vehicle_type: str,
    distance_km: float,
    duration_min: float,
    surge_multiplier: float = 1.0,
) -> dict[str, Decimal]:
    """Return fare breakdown as Decimals."""
    cfg = FARE_CONFIG.get(vehicle_type, FARE_CONFIG["mini"])

    base = Decimal(str(cfg["base"]))
    dist_fare = Decimal(str(distance_km)) * Decimal(str(cfg["per_km"]))
    time_fare = Decimal(str(duration_min)) * Decimal(str(cfg["per_min"]))
    surge = Decimal(str(surge_multiplier))
    min_fare = Decimal(str(cfg["min_fare"]))

    subtotal = base + dist_fare + time_fare
    surge_amount = subtotal * (surge - Decimal("1"))
    total = subtotal + surge_amount
    total = max(total, min_fare).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "base_fare": base.quantize(Decimal("0.01")),
        "distance_fare": dist_fare.quantize(Decimal("0.01")),
        "time_fare": time_fare.quantize(Decimal("0.01")),
        "surge_multiplier": surge.quantize(Decimal("0.01")),
        "total_fare": total,
    }


def estimate_fare(vehicle_type: str, distance_km: float, surge_multiplier: float = 1.0) -> Decimal:
    """Quick estimate using average speed assumption (25 km/h city driving)."""
    duration_min = (distance_km / 25.0) * 60 if distance_km > 0 else 0
    result = calculate_fare(vehicle_type, distance_km, duration_min, surge_multiplier)
    return result["total_fare"]

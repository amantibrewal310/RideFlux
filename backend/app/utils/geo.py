import math

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in kilometers between two lat/lng points."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_duration_minutes(distance_km: float, avg_speed_kmh: float = 25.0) -> float:
    """Rough ETA based on average city speed."""
    if avg_speed_kmh <= 0:
        return 0.0
    return (distance_km / avg_speed_kmh) * 60

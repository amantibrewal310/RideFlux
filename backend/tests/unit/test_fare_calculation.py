"""
Unit tests for fare calculation utilities (calculate_fare and estimate_fare).

Covers:
- Each vehicle type (auto, mini, sedan, suv) with known distance / duration
- Surge multiplier increases fare
- Minimum fare is enforced when distance is 0
- estimate_fare returns reasonable values
"""

from decimal import Decimal

import pytest

from app.utils.fare import FARE_CONFIG, calculate_fare, estimate_fare


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _expected_total(vehicle_type: str, distance_km: float, duration_min: float, surge: float = 1.0) -> Decimal:
    """Mirror the production formula so tests stay in sync with FARE_CONFIG."""
    cfg = FARE_CONFIG[vehicle_type]
    base = Decimal(str(cfg["base"]))
    dist_fare = Decimal(str(distance_km)) * Decimal(str(cfg["per_km"]))
    time_fare = Decimal(str(duration_min)) * Decimal(str(cfg["per_min"]))
    surge_d = Decimal(str(surge))
    min_fare = Decimal(str(cfg["min_fare"]))

    subtotal = base + dist_fare + time_fare
    surge_amount = subtotal * (surge_d - Decimal("1"))
    total = subtotal + surge_amount
    total = max(total, min_fare).quantize(Decimal("0.01"))
    return total


# -----------------------------------------------------------------------
# Per-vehicle-type tests
# -----------------------------------------------------------------------

class TestCalculateFareByVehicleType:
    """Validate that calculate_fare returns correct totals for each vehicle type."""

    DISTANCE_KM = 10.0
    DURATION_MIN = 20.0

    @pytest.mark.parametrize("vehicle_type", ["auto", "mini", "sedan", "suv"])
    def test_fare_matches_expected(self, vehicle_type: str):
        result = calculate_fare(vehicle_type, self.DISTANCE_KM, self.DURATION_MIN)
        expected = _expected_total(vehicle_type, self.DISTANCE_KM, self.DURATION_MIN)
        assert result["total_fare"] == expected

    @pytest.mark.parametrize("vehicle_type", ["auto", "mini", "sedan", "suv"])
    def test_breakdown_keys_present(self, vehicle_type: str):
        result = calculate_fare(vehicle_type, self.DISTANCE_KM, self.DURATION_MIN)
        assert set(result.keys()) == {
            "base_fare",
            "distance_fare",
            "time_fare",
            "surge_multiplier",
            "total_fare",
        }

    def test_auto_fare_values(self):
        result = calculate_fare("auto", 10, 20)
        assert result["base_fare"] == Decimal("25.00")
        assert result["distance_fare"] == Decimal("80.00")
        assert result["time_fare"] == Decimal("20.00")
        assert result["total_fare"] == Decimal("125.00")

    def test_mini_fare_values(self):
        result = calculate_fare("mini", 10, 20)
        assert result["base_fare"] == Decimal("40.00")
        assert result["distance_fare"] == Decimal("100.00")
        assert result["time_fare"] == Decimal("30.00")
        assert result["total_fare"] == Decimal("170.00")

    def test_sedan_fare_values(self):
        result = calculate_fare("sedan", 10, 20)
        assert result["base_fare"] == Decimal("60.00")
        assert result["distance_fare"] == Decimal("140.00")
        assert result["time_fare"] == Decimal("40.00")
        assert result["total_fare"] == Decimal("240.00")

    def test_suv_fare_values(self):
        result = calculate_fare("suv", 10, 20)
        assert result["base_fare"] == Decimal("80.00")
        assert result["distance_fare"] == Decimal("180.00")
        assert result["time_fare"] == Decimal("50.00")
        assert result["total_fare"] == Decimal("310.00")


# -----------------------------------------------------------------------
# Surge multiplier
# -----------------------------------------------------------------------

class TestCalculateFareSurge:
    def test_surge_increases_total(self):
        normal = calculate_fare("mini", 10, 20, surge_multiplier=1.0)
        surged = calculate_fare("mini", 10, 20, surge_multiplier=1.5)
        assert surged["total_fare"] > normal["total_fare"]

    def test_surge_2x_doubles_total(self):
        result = calculate_fare("mini", 10, 20, surge_multiplier=2.0)
        base_result = calculate_fare("mini", 10, 20, surge_multiplier=1.0)
        # 2x surge means total = subtotal * 2
        assert result["total_fare"] == base_result["total_fare"] * 2

    def test_surge_multiplier_stored_in_result(self):
        result = calculate_fare("sedan", 5, 10, surge_multiplier=1.75)
        assert result["surge_multiplier"] == Decimal("1.75")


# -----------------------------------------------------------------------
# Minimum fare enforcement
# -----------------------------------------------------------------------

class TestMinimumFare:
    @pytest.mark.parametrize("vehicle_type,min_fare", [
        ("auto", Decimal("30.00")),
        ("mini", Decimal("50.00")),
        ("sedan", Decimal("80.00")),
        ("suv", Decimal("100.00")),
    ])
    def test_zero_distance_returns_min_fare(self, vehicle_type: str, min_fare: Decimal):
        """When distance and duration are 0 the base fare alone may be below
        the minimum.  The function should clamp to min_fare."""
        result = calculate_fare(vehicle_type, 0, 0)
        assert result["total_fare"] >= min_fare

    def test_very_short_trip_auto_gets_min_fare(self):
        """auto base=25, per_km=8*0.1=0.8, per_min=1*0.5=0.5 -> 26.3 < 30 min."""
        result = calculate_fare("auto", 0.1, 0.5)
        assert result["total_fare"] == Decimal("30.00")


# -----------------------------------------------------------------------
# estimate_fare
# -----------------------------------------------------------------------

class TestEstimateFare:
    def test_estimate_returns_decimal(self):
        result = estimate_fare("mini", 10)
        assert isinstance(result, Decimal)

    def test_estimate_positive_for_positive_distance(self):
        result = estimate_fare("sedan", 5)
        assert result > 0

    def test_estimate_zero_distance_returns_min_fare(self):
        result = estimate_fare("auto", 0)
        assert result >= Decimal(str(FARE_CONFIG["auto"]["min_fare"]))

    def test_estimate_with_surge(self):
        normal = estimate_fare("suv", 8)
        surged = estimate_fare("suv", 8, surge_multiplier=2.0)
        assert surged > normal

    def test_estimate_reasonable_10km_mini(self):
        """A 10 km mini ride should cost somewhere between 100 and 500."""
        result = estimate_fare("mini", 10)
        assert Decimal("100") <= result <= Decimal("500")

    def test_unknown_vehicle_type_falls_back_to_mini(self):
        """Unknown vehicle types should use the mini config as default."""
        result = calculate_fare("unknown_type", 10, 20)
        expected = calculate_fare("mini", 10, 20)
        assert result["total_fare"] == expected["total_fare"]

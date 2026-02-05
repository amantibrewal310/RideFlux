from enum import Enum
from typing import Dict, Set

from app.core.exceptions import InvalidStateTransitionError


class RideStatus(str, Enum):
    PENDING = "pending"
    MATCHING = "matching"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DRIVER_EN_ROUTE = "driver_en_route"
    ARRIVED = "arrived"
    IN_TRIP = "in_trip"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_DRIVERS = "no_drivers"


class RideStateMachine:
    """
    Finite-state machine governing ride-request lifecycle.

    States
    ------
    pending -> matching -> offered -> accepted -> driver_en_route ->
    arrived -> in_trip -> completed

    Branches
    --------
    offered  -> matching    (driver declines / offer expires, re-match)
    offered  -> no_drivers  (max offers reached)
    {pending, matching, offered, accepted, driver_en_route, arrived} -> cancelled
    """

    _transitions: Dict[RideStatus, Set[RideStatus]] = {
        RideStatus.PENDING: {RideStatus.MATCHING, RideStatus.CANCELLED},
        RideStatus.MATCHING: {RideStatus.OFFERED, RideStatus.CANCELLED},
        RideStatus.OFFERED: {
            RideStatus.ACCEPTED,
            RideStatus.MATCHING,
            RideStatus.NO_DRIVERS,
            RideStatus.CANCELLED,
        },
        RideStatus.ACCEPTED: {RideStatus.DRIVER_EN_ROUTE, RideStatus.CANCELLED},
        RideStatus.DRIVER_EN_ROUTE: {RideStatus.ARRIVED, RideStatus.CANCELLED},
        RideStatus.ARRIVED: {RideStatus.IN_TRIP, RideStatus.CANCELLED},
        RideStatus.IN_TRIP: {RideStatus.COMPLETED},
        RideStatus.COMPLETED: set(),
        RideStatus.CANCELLED: set(),
        RideStatus.NO_DRIVERS: set(),
    }

    @classmethod
    def can_transition(cls, current: RideStatus, target: RideStatus) -> bool:
        """Return True if *target* is reachable from *current*."""
        return target in cls._transitions.get(current, set())

    @classmethod
    def transition(cls, current: RideStatus, target: RideStatus) -> RideStatus:
        """
        Validate and execute the state transition.

        Returns the new status on success; raises
        ``InvalidStateTransitionError`` otherwise.
        """
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(current.value, target.value)
        return target

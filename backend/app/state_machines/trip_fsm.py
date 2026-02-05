from enum import Enum
from typing import Dict, Set

from app.core.exceptions import InvalidStateTransitionError


class TripStatus(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TripStateMachine:
    """
    Finite-state machine governing trip lifecycle.

    Transitions
    -----------
    started     -> in_progress
    in_progress -> completed
    in_progress -> paused
    paused      -> in_progress  (resume)
    {started, in_progress, paused} -> cancelled
    """

    _transitions: Dict[TripStatus, Set[TripStatus]] = {
        TripStatus.STARTED: {TripStatus.IN_PROGRESS, TripStatus.CANCELLED},
        TripStatus.IN_PROGRESS: {
            TripStatus.COMPLETED,
            TripStatus.PAUSED,
            TripStatus.CANCELLED,
        },
        TripStatus.PAUSED: {TripStatus.IN_PROGRESS, TripStatus.CANCELLED},
        TripStatus.COMPLETED: set(),
        TripStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, current: TripStatus, target: TripStatus) -> bool:
        """Return True if *target* is reachable from *current*."""
        return target in cls._transitions.get(current, set())

    @classmethod
    def transition(cls, current: TripStatus, target: TripStatus) -> TripStatus:
        """
        Validate and execute the state transition.

        Returns the new status on success; raises
        ``InvalidStateTransitionError`` otherwise.
        """
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(current.value, target.value)
        return target

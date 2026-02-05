from enum import Enum
from typing import Dict, Set

from app.core.exceptions import InvalidStateTransitionError


class OfferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class OfferStateMachine:
    """
    Finite-state machine governing ride-offer lifecycle.

    Transitions
    -----------
    pending -> accepted
    pending -> declined
    pending -> expired
    """

    _transitions: Dict[OfferStatus, Set[OfferStatus]] = {
        OfferStatus.PENDING: {
            OfferStatus.ACCEPTED,
            OfferStatus.DECLINED,
            OfferStatus.EXPIRED,
        },
        OfferStatus.ACCEPTED: set(),
        OfferStatus.DECLINED: set(),
        OfferStatus.EXPIRED: set(),
    }

    @classmethod
    def can_transition(cls, current: OfferStatus, target: OfferStatus) -> bool:
        """Return True if *target* is reachable from *current*."""
        return target in cls._transitions.get(current, set())

    @classmethod
    def transition(cls, current: OfferStatus, target: OfferStatus) -> OfferStatus:
        """
        Validate and execute the state transition.

        Returns the new status on success; raises
        ``InvalidStateTransitionError`` otherwise.
        """
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(current.value, target.value)
        return target

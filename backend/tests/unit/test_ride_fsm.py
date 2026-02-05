"""
Unit tests for the Ride finite-state machine (RideStateMachine).

Covers:
- Happy-path transitions from pending through completed
- Re-match branch (offered -> matching)
- No-drivers branch (offered -> no_drivers)
- Cancellation from every valid state
- Invalid transitions raise InvalidStateTransitionError
- can_transition returns the correct boolean
"""

import pytest

from app.core.exceptions import InvalidStateTransitionError
from app.state_machines.ride_fsm import RideStateMachine, RideStatus


# -----------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------

class TestRideFSMHappyPath:
    """Walk through the full ride lifecycle."""

    def test_pending_to_matching(self):
        result = RideStateMachine.transition(RideStatus.PENDING, RideStatus.MATCHING)
        assert result == RideStatus.MATCHING

    def test_matching_to_offered(self):
        result = RideStateMachine.transition(RideStatus.MATCHING, RideStatus.OFFERED)
        assert result == RideStatus.OFFERED

    def test_offered_to_accepted(self):
        result = RideStateMachine.transition(RideStatus.OFFERED, RideStatus.ACCEPTED)
        assert result == RideStatus.ACCEPTED

    def test_accepted_to_driver_en_route(self):
        result = RideStateMachine.transition(RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE)
        assert result == RideStatus.DRIVER_EN_ROUTE

    def test_driver_en_route_to_arrived(self):
        result = RideStateMachine.transition(RideStatus.DRIVER_EN_ROUTE, RideStatus.ARRIVED)
        assert result == RideStatus.ARRIVED

    def test_arrived_to_in_trip(self):
        result = RideStateMachine.transition(RideStatus.ARRIVED, RideStatus.IN_TRIP)
        assert result == RideStatus.IN_TRIP

    def test_in_trip_to_completed(self):
        result = RideStateMachine.transition(RideStatus.IN_TRIP, RideStatus.COMPLETED)
        assert result == RideStatus.COMPLETED

    def test_full_happy_path_sequence(self):
        """Walk the complete happy-path in order."""
        states = [
            RideStatus.PENDING,
            RideStatus.MATCHING,
            RideStatus.OFFERED,
            RideStatus.ACCEPTED,
            RideStatus.DRIVER_EN_ROUTE,
            RideStatus.ARRIVED,
            RideStatus.IN_TRIP,
            RideStatus.COMPLETED,
        ]
        for current, target in zip(states[:-1], states[1:]):
            result = RideStateMachine.transition(current, target)
            assert result == target


# -----------------------------------------------------------------------
# Branch: re-match and no_drivers
# -----------------------------------------------------------------------

class TestRideFSMBranches:
    def test_offered_to_matching_rematch(self):
        """Driver declines or offer expires -- re-enter matching."""
        result = RideStateMachine.transition(RideStatus.OFFERED, RideStatus.MATCHING)
        assert result == RideStatus.MATCHING

    def test_offered_to_no_drivers(self):
        """Max offers exhausted -- no drivers available."""
        result = RideStateMachine.transition(RideStatus.OFFERED, RideStatus.NO_DRIVERS)
        assert result == RideStatus.NO_DRIVERS


# -----------------------------------------------------------------------
# Cancellation
# -----------------------------------------------------------------------

class TestRideFSMCancellation:
    @pytest.mark.parametrize(
        "state",
        [
            RideStatus.PENDING,
            RideStatus.MATCHING,
            RideStatus.OFFERED,
            RideStatus.ACCEPTED,
            RideStatus.DRIVER_EN_ROUTE,
            RideStatus.ARRIVED,
        ],
    )
    def test_cancellation_from_valid_states(self, state: RideStatus):
        result = RideStateMachine.transition(state, RideStatus.CANCELLED)
        assert result == RideStatus.CANCELLED

    def test_in_trip_cannot_be_cancelled(self):
        """Once the trip starts, cancellation is not allowed."""
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.IN_TRIP, RideStatus.CANCELLED)

    def test_completed_cannot_be_cancelled(self):
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.COMPLETED, RideStatus.CANCELLED)


# -----------------------------------------------------------------------
# Invalid transitions
# -----------------------------------------------------------------------

class TestRideFSMInvalidTransitions:
    def test_completed_to_pending_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.COMPLETED, RideStatus.PENDING)

    def test_cancelled_to_matching_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.CANCELLED, RideStatus.MATCHING)

    def test_no_drivers_to_matching_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.NO_DRIVERS, RideStatus.MATCHING)

    def test_pending_to_completed_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.PENDING, RideStatus.COMPLETED)

    def test_matching_to_in_trip_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.MATCHING, RideStatus.IN_TRIP)

    def test_in_trip_to_cancelled_raises(self):
        """in_trip only allows -> completed."""
        with pytest.raises(InvalidStateTransitionError):
            RideStateMachine.transition(RideStatus.IN_TRIP, RideStatus.CANCELLED)


# -----------------------------------------------------------------------
# can_transition
# -----------------------------------------------------------------------

class TestRideFSMCanTransition:
    def test_can_transition_returns_true_for_valid(self):
        assert RideStateMachine.can_transition(RideStatus.PENDING, RideStatus.MATCHING) is True

    def test_can_transition_returns_false_for_invalid(self):
        assert RideStateMachine.can_transition(RideStatus.COMPLETED, RideStatus.PENDING) is False

    def test_can_transition_offered_to_matching(self):
        assert RideStateMachine.can_transition(RideStatus.OFFERED, RideStatus.MATCHING) is True

    def test_can_transition_in_trip_to_cancelled_is_false(self):
        assert RideStateMachine.can_transition(RideStatus.IN_TRIP, RideStatus.CANCELLED) is False

    def test_can_transition_terminal_states_have_no_outgoing(self):
        for terminal in (RideStatus.COMPLETED, RideStatus.CANCELLED, RideStatus.NO_DRIVERS):
            for target in RideStatus:
                assert RideStateMachine.can_transition(terminal, target) is False

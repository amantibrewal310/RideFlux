"""
Unit tests for the Trip finite-state machine (TripStateMachine).

Covers:
- Happy path: started -> in_progress -> completed
- Pause / resume: in_progress -> paused -> in_progress
- Cancellation from started, in_progress, and paused
- Invalid transitions from completed and cancelled (terminal states)
"""

import pytest

from app.core.exceptions import InvalidStateTransitionError
from app.state_machines.trip_fsm import TripStateMachine, TripStatus


# -----------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------

class TestTripFSMHappyPath:
    def test_started_to_in_progress(self):
        result = TripStateMachine.transition(TripStatus.STARTED, TripStatus.IN_PROGRESS)
        assert result == TripStatus.IN_PROGRESS

    def test_in_progress_to_completed(self):
        result = TripStateMachine.transition(TripStatus.IN_PROGRESS, TripStatus.COMPLETED)
        assert result == TripStatus.COMPLETED

    def test_full_happy_path(self):
        """started -> in_progress -> completed"""
        states = [TripStatus.STARTED, TripStatus.IN_PROGRESS, TripStatus.COMPLETED]
        for current, target in zip(states[:-1], states[1:]):
            result = TripStateMachine.transition(current, target)
            assert result == target


# -----------------------------------------------------------------------
# Pause / resume
# -----------------------------------------------------------------------

class TestTripFSMPauseResume:
    def test_in_progress_to_paused(self):
        result = TripStateMachine.transition(TripStatus.IN_PROGRESS, TripStatus.PAUSED)
        assert result == TripStatus.PAUSED

    def test_paused_to_in_progress(self):
        result = TripStateMachine.transition(TripStatus.PAUSED, TripStatus.IN_PROGRESS)
        assert result == TripStatus.IN_PROGRESS

    def test_pause_resume_cycle(self):
        """in_progress -> paused -> in_progress -> completed"""
        state = TripStatus.IN_PROGRESS
        state = TripStateMachine.transition(state, TripStatus.PAUSED)
        assert state == TripStatus.PAUSED

        state = TripStateMachine.transition(state, TripStatus.IN_PROGRESS)
        assert state == TripStatus.IN_PROGRESS

        state = TripStateMachine.transition(state, TripStatus.COMPLETED)
        assert state == TripStatus.COMPLETED


# -----------------------------------------------------------------------
# Cancellation
# -----------------------------------------------------------------------

class TestTripFSMCancellation:
    @pytest.mark.parametrize(
        "state",
        [TripStatus.STARTED, TripStatus.IN_PROGRESS, TripStatus.PAUSED],
    )
    def test_cancellation_from_valid_states(self, state: TripStatus):
        result = TripStateMachine.transition(state, TripStatus.CANCELLED)
        assert result == TripStatus.CANCELLED


# -----------------------------------------------------------------------
# Invalid transitions from terminal states
# -----------------------------------------------------------------------

class TestTripFSMInvalidTransitions:
    @pytest.mark.parametrize("target", list(TripStatus))
    def test_completed_has_no_outgoing(self, target: TripStatus):
        with pytest.raises(InvalidStateTransitionError):
            TripStateMachine.transition(TripStatus.COMPLETED, target)

    @pytest.mark.parametrize("target", list(TripStatus))
    def test_cancelled_has_no_outgoing(self, target: TripStatus):
        with pytest.raises(InvalidStateTransitionError):
            TripStateMachine.transition(TripStatus.CANCELLED, target)

    def test_started_to_completed_raises(self):
        """Cannot skip in_progress and jump directly to completed."""
        with pytest.raises(InvalidStateTransitionError):
            TripStateMachine.transition(TripStatus.STARTED, TripStatus.COMPLETED)

    def test_started_to_paused_raises(self):
        """Cannot pause without starting progress first."""
        with pytest.raises(InvalidStateTransitionError):
            TripStateMachine.transition(TripStatus.STARTED, TripStatus.PAUSED)

    def test_paused_to_completed_raises(self):
        """Must resume before completing."""
        with pytest.raises(InvalidStateTransitionError):
            TripStateMachine.transition(TripStatus.PAUSED, TripStatus.COMPLETED)


# -----------------------------------------------------------------------
# can_transition
# -----------------------------------------------------------------------

class TestTripFSMCanTransition:
    def test_can_transition_true(self):
        assert TripStateMachine.can_transition(TripStatus.STARTED, TripStatus.IN_PROGRESS) is True

    def test_can_transition_false(self):
        assert TripStateMachine.can_transition(TripStatus.COMPLETED, TripStatus.STARTED) is False

    def test_can_transition_pause(self):
        assert TripStateMachine.can_transition(TripStatus.IN_PROGRESS, TripStatus.PAUSED) is True

    def test_can_transition_resume(self):
        assert TripStateMachine.can_transition(TripStatus.PAUSED, TripStatus.IN_PROGRESS) is True

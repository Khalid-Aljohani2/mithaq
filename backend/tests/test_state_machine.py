"""The change-request state machine.

Every allowed transition is exercised, and every forbidden one is asserted to
raise. The forbidden set is generated from the full cross product rather than
hand-listed, so a transition quietly added to the table fails this file.
"""

import itertools

import pytest

from app.domain.enums import TERMINAL_STATES, ActorType, CRState
from app.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    COMMITTING_TRANSITIONS,
    ForbiddenActorError,
    IllegalTransitionError,
    can_transition,
    is_committing,
    reachable_from,
    transition,
)

ALLOWED_PAIRS = sorted(
    (source, target) for source, targets in ALLOWED_TRANSITIONS.items() for target in targets
)
ALL_PAIRS = set(itertools.product(CRState, CRState))
FORBIDDEN_PAIRS = sorted(ALL_PAIRS - set(ALLOWED_PAIRS))


def test_every_state_appears_in_the_table() -> None:
    """A state missing from the table would silently have no exits."""
    assert set(ALLOWED_TRANSITIONS) == set(CRState)


@pytest.mark.parametrize(("source", "target"), ALLOWED_PAIRS, ids=lambda p: str(p))
def test_allowed_transitions_are_permitted(source: CRState, target: CRState) -> None:
    assert can_transition(source, target)
    assert transition(source, target, ActorType.HUMAN) is target


@pytest.mark.parametrize(("source", "target"), FORBIDDEN_PAIRS, ids=lambda p: str(p))
def test_forbidden_transitions_raise(source: CRState, target: CRState) -> None:
    assert not can_transition(source, target)
    with pytest.raises(IllegalTransitionError) as error:
        transition(source, target, ActorType.HUMAN)
    assert error.value.code == "ILLEGAL_TRANSITION"


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES), ids=lambda s: s.value)
def test_terminal_states_have_no_exit(state: CRState) -> None:
    assert reachable_from(state) == frozenset()


def test_a_request_cannot_skip_the_approval_chain() -> None:
    """RECOMMENDED goes to IN_APPROVAL, never straight to APPROVED."""
    assert not can_transition(CRState.RECOMMENDED, CRState.APPROVED)
    assert can_transition(CRState.RECOMMENDED, CRState.IN_APPROVAL)


def test_a_vo_cannot_be_issued_before_approval() -> None:
    for state in CRState:
        if state is not CRState.APPROVED:
            assert not can_transition(state, CRState.VO_ISSUED)


def test_in_scope_closure_is_terminal_and_only_from_analysis() -> None:
    sources = [s for s in CRState if can_transition(s, CRState.CLOSED_IN_SCOPE)]
    assert sources == [CRState.IN_ANALYSIS]
    assert reachable_from(CRState.CLOSED_IN_SCOPE) == frozenset()


# ---------------------------------------------------------------------------
# NFR-15 at the state-machine level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("source", "target"), sorted(COMMITTING_TRANSITIONS), ids=lambda p: str(p))
def test_ai_cannot_drive_a_committing_transition(source: CRState, target: CRState) -> None:
    """NFR-15: an AI actor may not commit the organisation to anything."""
    assert is_committing(source, target)
    with pytest.raises(ForbiddenActorError) as error:
        transition(source, target, ActorType.AI)
    assert error.value.code == "FORBIDDEN_ACTOR"
    # the same move is fine for a human
    assert transition(source, target, ActorType.HUMAN) is target


def test_ai_may_drive_non_committing_transitions() -> None:
    """Analysis itself is not a commitment, so it is not blocked."""
    assert transition(CRState.RECEIVED, CRState.IN_ANALYSIS, ActorType.AI) is CRState.IN_ANALYSIS


def test_every_committing_transition_is_actually_allowed() -> None:
    """A committing pair that is not in the table would be unreachable."""
    for source, target in COMMITTING_TRANSITIONS:
        assert can_transition(source, target), (source, target)


def test_approval_outcomes_are_all_committing() -> None:
    """Everything leaving IN_APPROVAL commits someone to something."""
    for target in reachable_from(CRState.IN_APPROVAL):
        assert is_committing(CRState.IN_APPROVAL, target), target

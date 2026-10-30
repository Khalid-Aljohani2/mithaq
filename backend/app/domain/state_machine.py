"""The change-request state machine.

Every transition the system permits is listed here, once. Anything not listed
is forbidden, and attempting it raises rather than silently succeeding.

This is where NFR-15 is enforced structurally: :func:`transition` takes an
``ActorType``, and the transitions that commit the organisation to something —
entering approval, approving, issuing a VO — are restricted to ``HUMAN`` or
``CODE``. An ``AI`` actor cannot drive them, whatever a model returns.
"""

from app.domain.enums import ActorType, CRState

#: Allowed moves, keyed by the state being left.
ALLOWED_TRANSITIONS: dict[CRState, frozenset[CRState]] = {
    CRState.RECEIVED: frozenset(
        {
            CRState.AWAITING_DOCUMENTS,  # stage 2 found gaps
            CRState.IN_ANALYSIS,  # documents complete
            CRState.REJECTED,  # a human rejects it outright
        }
    ),
    CRState.AWAITING_DOCUMENTS: frozenset(
        {
            CRState.IN_ANALYSIS,  # resubmitted and now complete
            CRState.REJECTED,
        }
    ),
    CRState.IN_ANALYSIS: frozenset(
        {
            CRState.CLOSED_IN_SCOPE,  # stage 3 says it is already in scope
            CRState.RECOMMENDED,  # stages 3-7 produced a recommendation
            CRState.REJECTED,
        }
    ),
    CRState.RECOMMENDED: frozenset(
        {
            CRState.IN_APPROVAL,  # the chain starts
            CRState.REJECTED,
            CRState.REVISION_REQUESTED,
        }
    ),
    CRState.IN_APPROVAL: frozenset(
        {
            CRState.IN_APPROVAL,  # an intermediate approver signed off
            CRState.APPROVED,  # the last approver signed off
            CRState.REJECTED,
            CRState.REVISION_REQUESTED,
        }
    ),
    CRState.REVISION_REQUESTED: frozenset(
        {
            CRState.IN_ANALYSIS,  # resubmitted, re-analysed from scratch
            CRState.REJECTED,
        }
    ),
    CRState.APPROVED: frozenset({CRState.VO_ISSUED}),
    CRState.VO_ISSUED: frozenset({CRState.IN_EXECUTION}),
    CRState.IN_EXECUTION: frozenset({CRState.CLOSED}),
    # Terminal.
    CRState.REJECTED: frozenset(),
    CRState.CLOSED_IN_SCOPE: frozenset(),
    CRState.CLOSED: frozenset(),
}

#: Transitions that commit the organisation. An AI actor may never drive these.
#: This is NFR-15 as a property of the state machine rather than a convention.
COMMITTING_TRANSITIONS: frozenset[tuple[CRState, CRState]] = frozenset(
    {
        (CRState.RECOMMENDED, CRState.IN_APPROVAL),
        (CRState.IN_APPROVAL, CRState.IN_APPROVAL),
        (CRState.IN_APPROVAL, CRState.APPROVED),
        (CRState.IN_APPROVAL, CRState.REJECTED),
        (CRState.IN_APPROVAL, CRState.REVISION_REQUESTED),
        (CRState.RECOMMENDED, CRState.REJECTED),
        (CRState.RECOMMENDED, CRState.REVISION_REQUESTED),
        (CRState.APPROVED, CRState.VO_ISSUED),
        (CRState.VO_ISSUED, CRState.IN_EXECUTION),
        (CRState.IN_EXECUTION, CRState.CLOSED),
    }
)


class IllegalTransitionError(Exception):
    """The requested move is not in :data:`ALLOWED_TRANSITIONS`."""

    def __init__(self, source: CRState, target: CRState) -> None:
        super().__init__(f"cannot move a change request from {source} to {target}")
        self.source = source
        self.target = target
        self.code = "ILLEGAL_TRANSITION"


class ForbiddenActorError(Exception):
    """An AI stage tried to drive a transition that commits the organisation."""

    def __init__(self, source: CRState, target: CRState, actor: ActorType) -> None:
        super().__init__(
            f"{actor} may not move a change request from {source} to {target}: "
            "this transition commits the organisation and requires a human decision "
            "(NFR-15)"
        )
        self.source = source
        self.target = target
        self.actor = actor
        self.code = "FORBIDDEN_ACTOR"


def can_transition(source: CRState, target: CRState) -> bool:
    """True when ``source -> target`` is a listed move."""
    return target in ALLOWED_TRANSITIONS.get(source, frozenset())


def is_committing(source: CRState, target: CRState) -> bool:
    """True when this move commits the organisation to something."""
    return (source, target) in COMMITTING_TRANSITIONS


def transition(source: CRState, target: CRState, actor: ActorType) -> CRState:
    """Validate a move and return the new state.

    Raises :class:`IllegalTransitionError` if the move is not allowed at all,
    or :class:`ForbiddenActorError` if an AI actor tried to drive a committing
    move. Returns the target state so callers read as an assignment.
    """
    if not can_transition(source, target):
        raise IllegalTransitionError(source, target)
    if actor is ActorType.AI and is_committing(source, target):
        raise ForbiddenActorError(source, target, actor)
    return target


def reachable_from(source: CRState) -> frozenset[CRState]:
    """States reachable in one move."""
    return ALLOWED_TRANSITIONS.get(source, frozenset())

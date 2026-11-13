"""The case lifecycle as a state machine.

Pure Python, no database, so it is trivial to test.
TRANSITIONS is the single source of truth: only the arrows listed here are allowed.
"""
from enum import Enum


class Status(str, Enum):
    DETECTED = "detected"
    PRIORITIZED = "prioritized"
    ASSIGNED = "assigned"
    INVESTIGATED = "investigated"
    INTERVENED = "intervened"
    VERIFYING = "verifying"
    CLOSED = "closed"


S = Status

# from_status -> {to_status: what this arrow means}
TRANSITIONS: dict[Status, dict[Status, str]] = {
    S.DETECTED: {S.PRIORITIZED: "Severity and priority scored"},
    S.PRIORITIZED: {S.ASSIGNED: "Manager assigns the case to a team"},
    S.ASSIGNED: {S.INVESTIGATED: "Field team has visited the site"},
    S.INVESTIGATED: {S.INTERVENED: "An action was taken on the ground"},
    S.INTERVENED: {S.VERIFYING: "Waiting for later imagery and field evidence"},
    S.VERIFYING: {
        S.CLOSED: "Resolved or improving: evidence confirms it",
        S.INTERVENED: "LOOP 1: needs more action, back for another intervention",
    },
    S.CLOSED: {S.DETECTED: "LOOP 2: closed cases stay monitored; new loss reopens the case"},
}


class TransitionError(Exception):
    """Base class so the API can catch every rejection in one place."""


class InvalidTransition(TransitionError):
    def __init__(self, current: Status, target: Status):
        self.current, self.target = current, target
        self.allowed = allowed_from(current)
        super().__init__(
            f"Cannot move a case from '{current.value}' to '{target.value}'. "
            f"Allowed next: {[s.value for s in self.allowed] or 'none'}"
        )


class ReasonRequired(TransitionError):
    pass


def parse_status(value: "str | Status") -> Status:
    try:
        return Status(value)
    except ValueError:
        raise TransitionError(
            f"Unknown status '{value}'. Valid: {[s.value for s in Status]}"
        ) from None


def allowed_from(current: "str | Status") -> list[Status]:
    return list(TRANSITIONS[parse_status(current)])


def validate_transition(current: "str | Status", target: "str | Status", reason: str) -> Status:
    """Return the target status if the move is legal, otherwise raise."""
    current, target = parse_status(current), parse_status(target)
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(current, target)
    if not reason or not reason.strip():
        raise ReasonRequired("Every status change needs a reason (it is the M&E record).")
    return target

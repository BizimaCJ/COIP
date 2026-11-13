"""Pure state-machine tests: no database needed."""
import itertools

import pytest

from app.state_machine import (
    TRANSITIONS, InvalidTransition, ReasonRequired, Status, TransitionError,
    allowed_from, validate_transition,
)

ALLOWED = [(a, b) for a, targets in TRANSITIONS.items() for b in targets]
FORBIDDEN = [p for p in itertools.product(Status, Status) if p not in ALLOWED]


def test_there_are_seven_statuses_and_eight_arrows():
    assert len(Status) == 7
    assert len(ALLOWED) == 8


@pytest.mark.parametrize("src,dst", ALLOWED)
def test_allowed_transition_passes(src, dst):
    assert validate_transition(src, dst, "because evidence") is dst


@pytest.mark.parametrize("src,dst", FORBIDDEN)
def test_every_other_transition_is_rejected(src, dst):
    with pytest.raises(InvalidTransition):
        validate_transition(src, dst, "because evidence")


def test_cannot_skip_straight_to_closed():
    with pytest.raises(InvalidTransition) as e:
        validate_transition("detected", "closed", "just close it")
    assert e.value.allowed == [Status.PRIORITIZED]


def test_verifying_is_the_decision_point():
    assert set(allowed_from("verifying")) == {Status.CLOSED, Status.INTERVENED}


def test_closed_cases_can_be_reopened():
    assert allowed_from("closed") == [Status.DETECTED]


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_reason_is_mandatory(reason):
    with pytest.raises(ReasonRequired):
        validate_transition("detected", "prioritized", reason)


def test_unknown_status_is_rejected():
    with pytest.raises(TransitionError):
        validate_transition("detected", "teleported", "x")


def test_full_happy_path():
    path = ["detected", "prioritized", "assigned", "investigated",
            "intervened", "verifying", "closed"]
    for a, b in zip(path, path[1:]):
        validate_transition(a, b, "ok")

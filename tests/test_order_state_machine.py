
from lunch_platform.domain.workflow import can_transition


def test_valid_transitions():
    assert can_transition("draft", "submitted")
    assert can_transition("submitted", "locked")
    assert can_transition("invoiced", "paid")


def test_invalid_transition_is_rejected():
    assert not can_transition("draft", "paid")
    assert not can_transition("cancelled", "draft")

import pytest

from provguard.schemas import Action, ActionOp, BoundingBox


def test_invalid_box_is_rejected() -> None:
    with pytest.raises(ValueError):
        BoundingBox(3, 0, 2, 1)


def test_action_cannot_have_two_target_forms() -> None:
    with pytest.raises(ValueError):
        Action(ActionOp.TAP, "o", target_region_id="n", coordinates=(1, 1))


import pytest

from stageflow.element import DictElement
from stageflow.lock import LockType, OrLogicLock, SimpleLock


def test_or_logic_first_group_passes():
    """First group passes → success."""
    element = DictElement({"work_done": "yes"})

    or_lock = OrLogicLock(
        condition_groups=[
            [SimpleLock({"type": LockType.EXISTS, "property_path": "work_done"})],
            [SimpleLock({"type": LockType.EXISTS, "property_path": "cancelled"})],
        ]
    )

    result = or_lock.validate(element)
    assert result.success is True
    assert result.passing_path == 1


def test_or_logic_second_group_passes():
    """First fails, second passes → success."""
    element = DictElement({"cancelled": True})

    or_lock = OrLogicLock(
        condition_groups=[
            [SimpleLock({"type": LockType.EXISTS, "property_path": "work_done"})],
            [SimpleLock({"type": LockType.EXISTS, "property_path": "cancelled"})],
        ]
    )

    result = or_lock.validate(element)
    assert result.success is True
    assert result.passing_path == 2


def test_or_logic_all_groups_fail():
    """All groups fail → failure."""
    element = DictElement({})

    or_lock = OrLogicLock(
        condition_groups=[
            [SimpleLock({"type": LockType.EXISTS, "property_path": "work_done"})],
            [SimpleLock({"type": LockType.EXISTS, "property_path": "cancelled"})],
        ]
    )

    result = or_lock.validate(element)
    assert result.success is False
    assert len(result.nested_failures) == 2


def test_or_logic_group_with_multiple_locks():
    """Group with multiple locks (AND logic) → all must pass."""
    element = DictElement(
        {
            "cancelled": True,
            "cancellation_reason": "Duplicate task",
            "approved_by": "manager",
        }
    )

    or_lock = OrLogicLock(
        condition_groups=[
            [SimpleLock({"type": LockType.EXISTS, "property_path": "work_done"})],
            [
                SimpleLock({"type": LockType.EXISTS, "property_path": "cancelled"}),
                SimpleLock(
                    {"type": LockType.EXISTS, "property_path": "cancellation_reason"}
                ),
                SimpleLock({"type": LockType.EXISTS, "property_path": "approved_by"}),
            ],
        ]
    )

    result = or_lock.validate(element)
    assert result.success is True
    assert result.passing_path == 2


def test_or_logic_short_circuit():
    """Short-circuit: stop at first passing group."""
    element = DictElement({"path1": "yes", "path2": "yes"})

    evaluation_count = [0]

    class CountingLock(SimpleLock):
        def validate(self, elem):
            evaluation_count[0] += 1
            return super().validate(elem)

    or_lock = OrLogicLock(
        condition_groups=[
            [CountingLock({"type": LockType.EXISTS, "property_path": "path1"})],
            [CountingLock({"type": LockType.EXISTS, "property_path": "path2"})],
            [CountingLock({"type": LockType.EXISTS, "property_path": "path3"})],
        ],
        short_circuit=True,
    )

    result = or_lock.validate(element)
    assert result.success is True
    assert evaluation_count[0] == 1  # Only first group evaluated


def test_or_logic_no_short_circuit():
    """Non-short-circuit: evaluate all groups."""
    element = DictElement({"path1": "yes", "path2": "yes"})

    or_lock = OrLogicLock(
        condition_groups=[
            [SimpleLock({"type": LockType.EXISTS, "property_path": "path1"})],
            [SimpleLock({"type": LockType.EXISTS, "property_path": "path2"})],
        ],
        short_circuit=False,
    )

    result = or_lock.validate(element)
    assert result.success is True
    assert "1" in result.context and "2" in result.context


def test_or_logic_empty_groups_raises():
    """Empty condition groups raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        OrLogicLock(condition_groups=[])
    assert "at least one" in str(exc_info.value)


def test_or_logic_empty_group_raises():
    """Empty group in list raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        OrLogicLock(
            condition_groups=[
                [SimpleLock({"type": LockType.EXISTS, "property_path": "field"})],
                [],  # Empty group
            ]
        )
    assert "empty" in str(exc_info.value).lower()


def test_or_logic_with_conditional():
    """OR_LOGIC can contain ConditionalLock."""
    from stageflow.lock import ConditionalLock

    element = DictElement({"type": "feature", "testing": "done"})

    or_lock = OrLogicLock(
        condition_groups=[
            [
                ConditionalLock(
                    if_locks=[
                        SimpleLock(
                            {
                                "type": LockType.EQUALS,
                                "property_path": "type",
                                "expected_value": "feature",
                            }
                        )
                    ],
                    then_locks=[
                        SimpleLock(
                            {"type": LockType.EXISTS, "property_path": "testing"}
                        )
                    ],
                )
            ],
            [SimpleLock({"type": LockType.EXISTS, "property_path": "cancelled"})],
        ]
    )

    result = or_lock.validate(element)
    assert result.success is True

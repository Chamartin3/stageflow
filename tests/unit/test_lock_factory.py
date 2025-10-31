import pytest

from stageflow.lock import LockFactory, OrLogicLock, SimpleLock


def test_factory_creates_or_logic_lock():
    """LockFactory creates OrLogicLock from config."""
    config = {
        "type": "OR_LOGIC",
        "conditions": [
            {"locks": [{"exists": "work_done"}]},
            {"locks": [{"exists": "cancelled"}]},
        ],
    }

    lock = LockFactory.create(config)

    assert isinstance(lock, OrLogicLock)
    assert len(lock.condition_groups) == 2
    assert lock.short_circuit is True


def test_factory_or_logic_with_short_circuit_false():
    """LockFactory handles short_circuit parameter."""
    config = {
        "type": "OR_LOGIC",
        "short_circuit": False,
        "conditions": [
            {"locks": [{"exists": "path1"}]},
            {"locks": [{"exists": "path2"}]},
        ],
    }

    lock = LockFactory.create(config)

    assert isinstance(lock, OrLogicLock)
    assert lock.short_circuit is False


def test_factory_or_logic_multiple_locks_per_group():
    """LockFactory handles multiple locks per group."""
    config = {
        "type": "OR_LOGIC",
        "conditions": [
            {
                "locks": [
                    {"exists": "work_done"},
                    {
                        "type": "GREATER_THAN",
                        "property_path": "quality",
                        "expected_value": 80,
                    },
                ]
            },
            {
                "locks": [
                    {
                        "type": "EQUALS",
                        "property_path": "cancelled",
                        "expected_value": True,
                    },
                    {"exists": "cancellation_reason"},
                ]
            },
        ],
    }

    lock = LockFactory.create(config)

    assert isinstance(lock, OrLogicLock)
    assert len(lock.condition_groups) == 2
    assert len(lock.condition_groups[0]) == 2
    assert len(lock.condition_groups[1]) == 2


def test_factory_or_logic_with_conditional():
    """OrLogicLock can contain ConditionalLock."""
    config = {
        "type": "OR_LOGIC",
        "conditions": [
            {
                "locks": [
                    {
                        "type": "CONDITIONAL",
                        "if": [{"exists": "type"}],
                        "then": [{"exists": "testing"}],
                    }
                ]
            },
            {"locks": [{"exists": "cancelled"}]},
        ],
    }

    lock = LockFactory.create(config)

    assert isinstance(lock, OrLogicLock)
    from stageflow.lock import ConditionalLock

    assert isinstance(lock.condition_groups[0][0], ConditionalLock)


def test_factory_or_logic_missing_conditions_raises():
    """Missing 'conditions' field raises ValueError."""
    config = {"type": "OR_LOGIC"}

    with pytest.raises(ValueError) as exc_info:
        LockFactory.create(config)
    assert "'conditions'" in str(exc_info.value)


def test_factory_or_logic_group_missing_locks_raises():
    """Condition group missing 'locks' raises ValueError."""
    config = {"type": "OR_LOGIC", "conditions": [{"invalid_field": []}]}

    with pytest.raises(ValueError) as exc_info:
        LockFactory.create(config)
    assert "'locks'" in str(exc_info.value)


def test_factory_or_logic_with_shorthand():
    """OrLogicLock works with shorthand syntax."""
    config = {
        "type": "OR_LOGIC",
        "conditions": [
            {"locks": [{"exists": "work_done"}, {"is_true": "approved"}]},
            {"locks": [{"exists": "cancelled"}]},
        ],
    }

    lock = LockFactory.create(config)

    assert isinstance(lock, OrLogicLock)
    assert all(
        isinstance(lock_item, SimpleLock)
        for group in lock.condition_groups
        for lock_item in group
    )

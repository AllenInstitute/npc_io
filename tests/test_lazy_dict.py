"""Regression tests for successful LazyDict values being cached exactly once."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from npc_io.lazy_dict import LazyDict


@pytest.mark.parametrize("value", [[], (), [1], (1,), "", {}, set(), None, 0, False])
def test_cached_values_are_returned_without_reinterpretation(value: object) -> None:
    factory = Mock(return_value=value)
    mapping = LazyDict(result=(factory, (), {}))

    assert mapping["result"] is value
    assert mapping["result"] is value
    factory.assert_called_once_with()


def test_factory_shaped_cached_value_is_not_executed() -> None:
    inner_factory = Mock(return_value="must not execute")
    value = (inner_factory, (), {})
    factory = Mock(return_value=value)
    mapping = LazyDict(result=(factory, (), {}))

    assert mapping["result"] is value
    assert mapping["result"] is value
    factory.assert_called_once_with()
    inner_factory.assert_not_called()


def test_mapping_accessors_reuse_cached_empty_values() -> None:
    factory = Mock(return_value=[])
    mapping = LazyDict(empty=(factory, (), {}))

    assert dict(mapping.items()) == {"empty": []}
    assert dict(mapping.items()) == {"empty": []}
    assert mapping.get("empty") == []
    assert mapping.get("missing") is None
    factory.assert_called_once_with()


def test_failed_evaluation_is_not_cached() -> None:
    factory = Mock(side_effect=[RuntimeError("unavailable"), []])
    mapping = LazyDict(result=(factory, (), {}))

    with pytest.raises(RuntimeError, match="unavailable"):
        mapping["result"]
    assert mapping["result"] == []
    assert mapping["result"] == []
    assert factory.call_count == 2

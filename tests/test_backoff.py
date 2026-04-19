"""Tests for backoff strategies."""

import pytest
from procwatch.backoff import constant, linear, exponential, from_config


def take(n, iterator):
    return [next(iterator) for _ in range(n)]


def test_constant():
    gen = constant(5.0)
    assert take(3, gen) == [5.0, 5.0, 5.0]


def test_linear():
    gen = linear(1.0, 2.0, maximum=10.0)
    assert take(4, gen) == [1.0, 3.0, 5.0, 7.0]


def test_linear_caps_at_maximum():
    gen = linear(1.0, 5.0, maximum=8.0)
    values = take(5, gen)
    assert all(v <= 8.0 for v in values)


def test_exponential():
    gen = exponential(1.0, factor=2.0, maximum=16.0)
    assert take(5, gen) == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_exponential_caps():
    gen = exponential(1.0, factor=10.0, maximum=50.0)
    values = take(6, gen)
    assert all(v <= 50.0 for v in values)


def test_exponential_jitter():
    gen = exponential(10.0, jitter=True)
    values = take(10, gen)
    assert all(0.0 <= v <= 10.0 for v in values)


def test_from_config_constant():
    gen = from_config("constant", delay=3.0)
    assert next(gen) == 3.0


def test_from_config_unknown():
    with pytest.raises(ValueError, match="Unknown backoff strategy"):
        from_config("random_walk")

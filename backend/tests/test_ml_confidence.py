"""Class-count-aware confidence gating.

Regression guard for a real bug: the original fixed 0.55 threshold made the ML
branch unreachable with 13 categories (measured max confidence on the seeded
corpus was 0.34), so the model trained successfully and then never once decided
a category.
"""
import numpy as np
import pytest

from app.config import settings
from app.ml.inference.categoriser_service import _accept, confidence_threshold


def test_threshold_scales_with_class_count():
    # More classes -> a lower bar, because probability mass is split more ways.
    assert confidence_threshold(13) < confidence_threshold(5)
    assert confidence_threshold(5) < confidence_threshold(2)


def test_threshold_is_reachable_for_many_classes():
    """The bug in one assertion: with 13 classes the bar must sit below what a
    real model actually produces (~0.34 max on this data)."""
    assert confidence_threshold(13) < 0.34


def test_threshold_respects_floor_and_ceiling():
    # Very many classes would drive the raw value to ~0; the floor catches it.
    assert confidence_threshold(1000) == settings.ml_confidence_floor
    # Very few classes would drive it above 1.0; the ceiling catches it.
    assert confidence_threshold(2) == settings.ml_confidence_ceiling
    assert confidence_threshold(1) == settings.ml_confidence_ceiling


def test_threshold_beats_random_baseline():
    """Whatever the class count, the bar must be meaningfully above a coin flip
    among the classes -- otherwise we'd accept noise."""
    for n in (5, 10, 13, 20):
        assert confidence_threshold(n) > 1.0 / n


def test_accept_rejects_low_confidence():
    # 13 classes, essentially uniform -> must defer to rules.
    proba = np.full(13, 1 / 13)
    accepted, conf, _ = _accept(proba)
    assert accepted is False
    assert conf == pytest.approx(1 / 13)


def test_accept_takes_clear_winner():
    proba = np.full(13, 0.02)
    proba[3] = 0.74
    accepted, conf, margin = _accept(proba)
    assert accepted is True
    assert conf == pytest.approx(0.74)
    assert margin > settings.ml_confidence_margin


def test_accept_rejects_near_tie_even_above_threshold():
    """Two plausible categories a hair apart is a coin flip, not a decision --
    the margin check must veto it even though top-1 clears the threshold."""
    proba = np.full(13, 0.01)
    proba[2] = 0.44
    proba[7] = 0.43          # margin of 0.01, below ml_confidence_margin
    accepted, conf, margin = _accept(proba)
    assert conf > confidence_threshold(13)   # would have passed on confidence alone
    assert margin < settings.ml_confidence_margin
    assert accepted is False

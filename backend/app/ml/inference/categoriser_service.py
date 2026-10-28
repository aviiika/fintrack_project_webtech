"""
ML inference service — the categoriser that actually runs in production.

Design rationale:
    - Confidence-gated fallback ("selective prediction"): an uncertain model
      shouldn't guess, it should defer to the keyword rules. This is the key
      safety mechanism in the whole pipeline.
    - The gate is computed from the number of classes, not hardcoded — see
      confidence_threshold() below for why that matters.
    - Model is cached via lru_cache so we don't hit disk on every request.
    - The registry's set_active_model() invalidates this cache after retraining,
      so a freshly-trained model goes live immediately with no server restart.
"""
import logging
from functools import lru_cache

import joblib
import numpy as np

from app.config import settings
from app.ml.features.text_features import clean_description
from app.ml.registry import get_active_model_info
from app.services.categoriser import categorise as rule_based_categorise

logger = logging.getLogger(__name__)


def confidence_threshold(n_classes: int) -> float:
    """Minimum softmax probability before we trust the model over the rules.

    Scaled to the number of categories instead of fixed, because "confidence"
    means different things at different class counts. With 13 categories a
    uniform guess sits at 1/13 = 0.077, and a genuinely good prediction on short,
    noisy bank descriptions tops out around 0.30-0.35. A fixed 0.55 -- a sane
    number for a binary classifier -- is therefore unreachable here: measured
    across the full seeded corpus the maximum confidence any row achieved was
    0.34, so the ML branch never executed once.

    The rule: demand `multiplier` times better than a random guess, clamped to a
    sane absolute range.

        threshold = clamp(multiplier / n_classes, floor, ceiling)

    At 13 classes that gives 2.5/13 = 0.19, which on the seeded data claims ~45%
    of rows at 100% agreement with the hand-written rules -- i.e. the model only
    speaks up where it's actually right, and stays quiet elsewhere.
    """
    if n_classes < 2:
        return settings.ml_confidence_ceiling
    raw = settings.ml_confidence_multiplier / n_classes
    return min(settings.ml_confidence_ceiling, max(settings.ml_confidence_floor, raw))


def _accept(proba) -> tuple[bool, float, float]:
    """Decide whether to trust the top prediction.

    Two conditions, both necessary:
      1. top-1 probability clears the class-count-aware threshold;
      2. top-1 beats top-2 by at least `ml_confidence_margin`.

    The margin check exists because probability mass alone can't distinguish
    "clearly Groceries" from "a near-tie between Groceries and Food & Dining
    that happened to land one basis point apart". A coin-flip between two
    plausible categories should defer to the rules, not be reported as an
    ML decision.
    """
    order = np.argsort(proba)
    top1 = float(proba[order[-1]])
    top2 = float(proba[order[-2]]) if len(proba) > 1 else 0.0
    margin = top1 - top2
    ok = top1 >= confidence_threshold(len(proba)) and margin >= settings.ml_confidence_margin
    return ok, top1, margin


@lru_cache(maxsize=1)
def _load_model():
    """Load the active model from disk. Cached — invalidated on retrain."""
    info = get_active_model_info()
    if info is None:
        return None
    try:
        model = joblib.load(info["active_model_path"])
        logger.info("Loaded ML categoriser from %s", info["active_model_path"])
        return model
    except Exception as e:  # noqa: BLE001 - a corrupt/incompatible artifact must
        # degrade to rules, never take the API down. Any load failure is the same
        # failure from the caller's point of view: there is no usable model.
        logger.error("Failed to load ML model: %s. Falling back to rules.", e)
        return None


def predict_category(description: str, txn_type: str = "debit") -> dict:
    """Predict a category for a single transaction description.

    Returns a dict shaped like app.schemas.all.CategoryPrediction:
        {
          "category": str,
          "source": "ml" | "rules_low_confidence" | "rules_no_model",
          "confidence": float | None,
          "rules_fallback_reason": str | None,
        }
    """
    model = _load_model()

    # Case 1: no model trained yet → fall back to rules
    if model is None:
        return {
            "category": rule_based_categorise(description, txn_type),
            "source": "rules_no_model",
            "confidence": None,
            "rules_fallback_reason": "No ML model has been trained yet.",
        }

    cleaned = clean_description(description)
    if not cleaned:
        # Pathological empty-after-cleaning case — give rules a shot
        return {
            "category": rule_based_categorise(description, txn_type),
            "source": "rules_low_confidence",
            "confidence": 0.0,
            "rules_fallback_reason": "Description was empty after cleaning.",
        }

    proba = model.predict_proba([cleaned])[0]
    best_idx = int(proba.argmax())
    predicted = str(model.classes_[best_idx])
    accepted, confidence, margin = _accept(proba)

    # Case 2: confident ML prediction → use it
    if accepted:
        return {
            "category": predicted,
            "source": "ml",
            "confidence": confidence,
            "rules_fallback_reason": None,
        }

    # Case 3: not confident enough → defer to rules
    threshold = confidence_threshold(len(proba))
    reason = (
        f"ML confidence {confidence:.2f} below threshold {threshold:.2f}"
        if confidence < threshold
        else f"Top-2 margin {margin:.2f} too narrow (needs {settings.ml_confidence_margin:.2f})"
    )
    return {
        "category": rule_based_categorise(description, txn_type),
        "source": "rules_low_confidence",
        "confidence": confidence,
        "rules_fallback_reason": f"{reason}; ML would have predicted '{predicted}'.",
    }


def predict_batch(descriptions: list[tuple[str, str]]) -> list[dict]:
    """Batch prediction — used during CSV import to avoid per-row overhead.

    Input: list of (description, txn_type) tuples.
    Output: list of prediction dicts, one per input.
    """
    model = _load_model()
    if model is None:
        return [
            {
                "category": rule_based_categorise(d, t),
                "source": "rules_no_model",
                "confidence": None,
                "rules_fallback_reason": "No ML model trained.",
            }
            for d, t in descriptions
        ]

    cleaned = [clean_description(d) for d, _ in descriptions]
    probas = model.predict_proba(cleaned)
    results = []
    for (desc, ttype), p in zip(descriptions, probas):
        pred = str(model.classes_[int(p.argmax())])
        accepted, conf, _margin = _accept(p)
        if accepted:
            results.append({"category": pred, "source": "ml", "confidence": conf,
                            "rules_fallback_reason": None})
        else:
            results.append({
                "category": rule_based_categorise(desc, ttype),
                "source": "rules_low_confidence",
                "confidence": conf,
                "rules_fallback_reason": f"Low confidence {conf:.2f}; ML suggested '{pred}'.",
            })
    return results

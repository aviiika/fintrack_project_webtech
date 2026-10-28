"""
Train the transaction categoriser from the user's own labelled transactions.

Design rationale:
    - TF-IDF + Logistic Regression → chosen deliberately over neural nets:
        * Trains in <1s on realistic data volumes (<10k rows per user)
        * Fully interpretable — predict_proba() gives us confidence scores,
          which is what powers the fallback-to-rules mechanism in inference
        * No GPU; runs anywhere Python runs
        * Genuinely competitive accuracy for short-text classification
    - User-corrected transactions are weighted 2x (sample_weight) because
      those are the labels we trust most — they came from an actual human
      who overrode the system.

Run standalone:    uv run python -m app.ml.training.train_categoriser
Called from API:   POST /api/v1/ml/retrain
"""
import logging
from collections import Counter
from datetime import datetime

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sqlalchemy import select

from app.config import settings
from app.database.session import SessionLocal
from app.ml.features.text_features import clean_description
from app.ml.registry import set_active_model
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


def _load_training_data(db, owner_id: int | None = None):
    """Load all categorised transactions. Returns (X, y, weights, meta)."""
    stmt = select(Transaction).where(
        Transaction.category.isnot(None),
        Transaction.category != "Uncategorized",
    )
    if owner_id is not None:
        stmt = stmt.where(Transaction.owner_id == owner_id)

    txns = list(db.scalars(stmt))

    X = [clean_description(t.description) for t in txns]
    y = [t.category for t in txns]
    # Weight user-corrected rows 2x — human-verified labels are our gold truth
    sample_weight = [2.0 if t.user_corrected else 1.0 for t in txns]
    return X, y, sample_weight


def _build_pipeline() -> Pipeline:
    """TF-IDF (unigrams + bigrams) → Logistic Regression (one-vs-rest)."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,  # dampens runaway term frequencies
                    lowercase=False,     # we already lowercased in cleaning
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",  # handles the Income-vs-everything-else imbalance
                    C=1.0,
                    solver="lbfgs",           # supports native multiclass; good for small datasets
                ),
            ),
        ]
    )


def train(owner_id: int | None = None, db=None) -> dict:
    """Train on all available labelled data.

    Returns a result dict with status/message/metrics suitable for an API response.

    If `db` is provided, uses that session (useful for tests + for picking up
    uncommitted data when triggered inline from a request). Otherwise opens
    a fresh session via SessionLocal (standalone / scheduled job path).
    """
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True
    try:
        X, y, sw = _load_training_data(db, owner_id=owner_id)
    finally:
        if close_after:
            db.close()

    n = len(X)
    min_required = settings.ml_min_training_samples

    if n < min_required:
        return {
            "status": "insufficient_data",
            "message": f"Need {min_required} categorised transactions to train. Have {n}.",
            "samples_available": n,
        }

    # Need at least 2 of each class or the stratified split dies
    class_counts = Counter(y)
    rare_classes = [c for c, cnt in class_counts.items() if cnt < 2]
    if rare_classes:
        # Fall back to a non-stratified split
        X_train, X_test, y_train, y_test, sw_train, _ = train_test_split(
            X, y, sw, test_size=0.2, random_state=42
        )
    else:
        X_train, X_test, y_train, y_test, sw_train, _ = train_test_split(
            X, y, sw, test_size=0.2, random_state=42, stratify=y
        )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train, clf__sample_weight=sw_train)

    # ── Evaluation ───────────────────────────────────────────────────────────
    y_pred = pipeline.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))

    # Per-class F1 — makes it easy to see which categories the model struggles on
    labels = sorted(set(y_test) | set(y_pred))
    f1_scores = f1_score(y_test, y_pred, labels=labels, average=None, zero_division=0)
    per_class_f1 = {label: float(score) for label, score in zip(labels, f1_scores)}

    # Confusion matrix — stored as nested dict for easy JSON serialisation
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_dict = {
        "labels": labels,
        "matrix": cm.tolist(),
    }

    classification_rep = classification_report(y_test, y_pred, zero_division=0)
    logger.info("Trained categoriser: accuracy=%.3f on %d samples", accuracy, n)
    logger.info("\n%s", classification_rep)

    # ── Save versioned artifact ──────────────────────────────────────────────
    version = datetime.now().strftime("v%Y%m%d_%H%M%S")
    model_path = settings.ml_models_path / f"categoriser_{version}.joblib"
    joblib.dump(pipeline, model_path)

    # ── Register as active model ─────────────────────────────────────────────
    classes = list(pipeline.classes_)
    set_active_model(
        path=str(model_path),
        accuracy=accuracy,
        sample_count=n,
        classes=classes,
        per_class_f1=per_class_f1,
        confusion_matrix=cm_dict,
    )

    return {
        "status": "trained",
        "message": f"Trained new model with {accuracy:.1%} accuracy on {n} samples.",
        "accuracy": accuracy,
        "samples": n,
        "version": version,
        "model_path": str(model_path),
        "per_class_f1": per_class_f1,
    }


if __name__ == "__main__":
    import json
    from app.utils.logging import configure_logging
    configure_logging()
    result = train()
    print(json.dumps(result, indent=2, default=str))

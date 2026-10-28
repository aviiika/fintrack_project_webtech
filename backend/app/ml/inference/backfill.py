"""Re-categorise existing transactions once a model exists.

Why this is needed: predictions happen at import time. The very first import
necessarily happens before any model has been trained (there's nothing to train
on yet), so those rows are categorised by keyword rules and carry
category_source='rules_no_model' forever -- even after a model is trained from
them minutes later.

This pass fixes that asymmetry by re-running inference over rows the model never
got a say on.

Two rules it must never break:
  1. user_corrected rows are NEVER touched. A human already overruled the system
     on those; silently re-predicting over a correction would both destroy the
     user's intent and poison the next training round, since corrections are the
     2x-weighted gold labels.
  2. It's a no-op when no model is active -- there's nothing better than rules to
     offer, so it leaves the rows alone rather than churning them.
"""
import logging

from sqlalchemy import select

from app.ml.inference.categoriser_service import predict_batch
from app.ml.registry import get_active_model_info
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


def backfill_predictions(db, owner_id: int | None = None) -> dict:
    """Re-predict categories for non-user-corrected transactions.

    Returns a summary dict: how many rows were examined, how many the model was
    confident enough to claim, and how many actually changed category.
    """
    if get_active_model_info() is None:
        return {"status": "no_model", "examined": 0, "ml_assigned": 0, "changed": 0}

    stmt = select(Transaction).where(Transaction.user_corrected.is_(False))
    if owner_id is not None:
        stmt = stmt.where(Transaction.owner_id == owner_id)
    rows = list(db.scalars(stmt))
    if not rows:
        return {"status": "nothing_to_do", "examined": 0, "ml_assigned": 0, "changed": 0}

    predictions = predict_batch([(t.description, t.txn_type) for t in rows])

    ml_assigned = changed = 0
    for txn, pred in zip(rows, predictions):
        if pred["category"] != txn.category:
            changed += 1
        txn.category = pred["category"]
        txn.category_source = pred["source"]
        txn.category_confidence = pred["confidence"]
        if pred["source"] == "ml":
            ml_assigned += 1

    db.commit()
    logger.info("Backfill: %d examined, %d claimed by ML, %d re-categorised",
                len(rows), ml_assigned, changed)
    return {"status": "done", "examined": len(rows),
            "ml_assigned": ml_assigned, "changed": changed}

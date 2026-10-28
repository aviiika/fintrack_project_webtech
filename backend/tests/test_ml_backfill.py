"""Backfill re-categorises rows imported before a model existed."""
from app.ml.inference.backfill import backfill_predictions
from app.models.transaction import Transaction


def test_backfill_is_noop_without_a_model(client, db_session):
    result = backfill_predictions(db_session)
    assert result["status"] == "no_model"
    assert result["ml_assigned"] == 0


def test_backfill_assigns_ml_source_after_training(seeded_client, db_session):
    client, auth_headers = seeded_client

    # Imported before any model existed -> everything is rules-sourced.
    before = db_session.query(Transaction).all()
    assert all(t.category_source == "rules_no_model" for t in before)

    assert client.post("/api/v1/ml/retrain", headers=auth_headers).json()["status"] == "trained"

    result = backfill_predictions(db_session)
    assert result["status"] == "done"
    assert result["examined"] > 0
    # With a model present, at least some rows should now be ML-sourced.
    assert result["ml_assigned"] > 0

    sources = {t.category_source for t in db_session.query(Transaction).all()}
    assert "ml" in sources


def test_backfill_never_overwrites_a_user_correction(seeded_client, db_session):
    """The critical invariant: corrections are the 2x-weighted gold labels that
    train the next model. Re-predicting over them would erase the human's intent
    and feed the model its own output as ground truth."""
    client, auth_headers = seeded_client
    client.post("/api/v1/ml/retrain", headers=auth_headers)

    txn = db_session.query(Transaction).first()
    client.patch(f"/api/v1/transactions/{txn.id}",
                 json={"category": "Entertainment"}, headers=auth_headers)
    db_session.expire_all()

    corrected = db_session.query(Transaction).filter_by(id=txn.id).one()
    assert corrected.user_corrected is True
    assert corrected.category == "Entertainment"

    backfill_predictions(db_session)
    db_session.expire_all()

    after = db_session.query(Transaction).filter_by(id=txn.id).one()
    assert after.category == "Entertainment"
    assert after.category_source == "manual"
    assert after.user_corrected is True

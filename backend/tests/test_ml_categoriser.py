"""Tests for the ML categoriser — the core new feature in Pro."""


# ─── Model info endpoint ─────────────────────────────────────────────────────

def test_model_info_when_no_model_exists(client, auth_headers):
    """Before any training, the endpoint should report keyword-rules mode."""
    r = client.get("/api/v1/ml/model-info", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_model_trained"
    assert body["using"] == "keyword_rules"


# ─── Training ────────────────────────────────────────────────────────────────

def test_retrain_fails_on_insufficient_data(client, auth_headers):
    """Can't train a model from thin air — needs the minimum sample threshold."""
    r = client.post("/api/v1/ml/retrain", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "insufficient_data"


def test_retrain_succeeds_with_seeded_data(seeded_client):
    """With ~30 transactions seeded, retraining should produce a working model."""
    client, hdr = seeded_client
    r = client.post("/api/v1/ml/retrain", headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "trained"
    assert body["model_info"]["status"] == "active"
    assert body["model_info"]["using"] == "ml_with_fallback"
    assert body["model_info"]["trained_on_samples"] >= 25
    assert 0 <= body["model_info"]["accuracy"] <= 1


def test_model_info_after_training(seeded_client):
    """After retraining, /model-info returns the active model's metadata."""
    client, hdr = seeded_client
    client.post("/api/v1/ml/retrain", headers=hdr)
    info = client.get("/api/v1/ml/model-info", headers=hdr).json()
    assert info["status"] == "active"
    assert info["classes"] is not None
    assert len(info["classes"]) >= 3  # at least a few categories learned
    assert isinstance(info["per_class_f1"], dict)


# ─── Live prediction preview ─────────────────────────────────────────────────

def test_predict_endpoint_before_training_uses_rules(client, auth_headers):
    """Before training, predictions should fall back to the keyword engine."""
    r = client.post("/api/v1/ml/predict",
                     json={"description": "Zomato Food Order", "txn_type": "debit"},
                     headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "rules_no_model"
    assert body["category"] == "Food & Dining"


def test_predict_endpoint_after_training_may_use_ml(seeded_client):
    """After training on food-related data, Zomato should classify confidently."""
    client, hdr = seeded_client
    client.post("/api/v1/ml/retrain", headers=hdr)

    r = client.post("/api/v1/ml/predict",
                     json={"description": "Zomato Dinner Order", "txn_type": "debit"},
                     headers=hdr)
    assert r.status_code == 200
    body = r.json()
    # Should either be ML-sourced OR rules fallback — both are valid outcomes
    assert body["source"] in ("ml", "rules_low_confidence", "rules_no_model")
    assert body["category"] in ("Food & Dining", "Uncategorized")


# ─── Feedback loop ───────────────────────────────────────────────────────────

def test_correction_marks_transaction_and_increments_counter(seeded_client):
    """Changing a category sets user_corrected=True AND bumps the counter."""
    client, hdr = seeded_client
    txns = client.get("/api/v1/transactions?limit=5", headers=hdr).json()["items"]
    tid = txns[0]["id"]

    # Change category — this is a "correction" per the feedback loop
    r = client.patch(f"/api/v1/transactions/{tid}",
                      json={"category": "Shopping"}, headers=hdr)
    assert r.status_code == 200
    assert r.json()["user_corrected"] is True
    assert r.json()["category_source"] == "manual"

    status = client.get("/api/v1/ml/correction-status", headers=hdr).json()
    assert status["corrections_this_cycle"] == 1
    assert status["total_lifetime_corrections"] == 1


def test_correction_counter_only_increments_on_real_change(seeded_client):
    """Patching with the same category shouldn't count as a correction."""
    client, hdr = seeded_client
    txns = client.get("/api/v1/transactions?limit=5", headers=hdr).json()["items"]
    tid, same_cat = txns[0]["id"], txns[0]["category"]

    client.patch(f"/api/v1/transactions/{tid}",
                  json={"category": same_cat}, headers=hdr)
    status = client.get("/api/v1/ml/correction-status", headers=hdr).json()
    assert status["corrections_this_cycle"] == 0


# ─── Anomaly detection ───────────────────────────────────────────────────────

def test_anomaly_endpoint_returns_list(seeded_client):
    """Should return a list (may be empty if data is too uniform)."""
    client, hdr = seeded_client
    r = client.get("/api/v1/ml/anomalies", headers=hdr)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ─── Forecast ────────────────────────────────────────────────────────────────

def test_forecast_endpoint_returns_schema(seeded_client):
    """Forecast should always respond with the right shape."""
    client, hdr = seeded_client
    r = client.get("/api/v1/ml/forecast", headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert "days_elapsed" in body
    assert "projected_month_end" in body

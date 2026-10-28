"""Net worth = cash (from the transaction ledger) + investments - liabilities."""


def test_networth_with_no_data_is_zero(client, auth_headers):
    r = client.get("/api/v1/networth", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["cash_balance"] == 0
    assert body["net_worth"] == 0
    assert body["liabilities"] == []


def test_networth_combines_cash_investments_and_liabilities(seeded_client, mock_stock_prices):
    client, auth_headers = seeded_client

    # From seeded_client: salary 52000 + freelance 8000 credited, minus a large set of
    # debits -- the exact cash figure isn't the point, just that it flows through.
    cash_before = client.get("/api/v1/networth", headers=auth_headers).json()["cash_balance"]

    client.post("/api/v1/portfolio/holdings",
                json={"symbol": "RELIANCE", "quantity": 10, "avg_buy_price": 2000.0},
                headers=auth_headers)  # mocked price 2500 -> current value 25000

    client.post("/api/v1/loans", json={
        "name": "Personal Loan", "liability_type": "personal_loan",
        "principal_amount": 100_000, "interest_rate_annual": 12.0,
        "tenure_months": 24, "start_date": "2024-01-01",
    }, headers=auth_headers)

    r = client.get("/api/v1/networth", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()

    assert body["cash_balance"] == cash_before
    assert body["investments_value"] == 25000.0
    assert len(body["liabilities"]) == 1
    assert body["total_liabilities"] == body["liabilities"][0]["outstanding_balance"]
    assert body["total_assets"] == round(cash_before + 25000.0, 2)
    assert body["net_worth"] == round(body["total_assets"] - body["total_liabilities"], 2)


def test_snapshot_and_history(client, auth_headers):
    r = client.post("/api/v1/networth/snapshot", headers=auth_headers)
    assert r.status_code == 200
    snap = r.json()
    assert "date" in snap and "net_worth" in snap

    # Re-snapshotting the same day should upsert, not duplicate
    client.post("/api/v1/networth/snapshot", headers=auth_headers)

    r = client.get("/api/v1/networth/history", headers=auth_headers)
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 1
    assert history[0]["date"] == snap["date"]

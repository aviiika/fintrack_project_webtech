def test_list_and_filter(seeded_client):
    client, hdr = seeded_client
    assert client.get("/api/v1/transactions", headers=hdr).json()["total"] == 31
    assert client.get("/api/v1/transactions?txn_type=credit", headers=hdr).json()["total"] == 2
    assert client.get("/api/v1/transactions?month=2025-05", headers=hdr).json()["total"] == 31

def test_dashboard(seeded_client):
    client, hdr = seeded_client
    body = client.get("/api/v1/dashboard?month=2025-05", headers=hdr).json()
    assert body["total_income"] == 60000.0
    assert body["debit_count"] == 29


def test_dashboard_bank_filter_scopes_every_figure(seeded_client):
    """Regression: the bank filter used to scope only the recent list. Totals, the
    category split and the trend must all follow it, and per-bank figures must add
    back up to the all-banks figures."""
    client, hdr = seeded_client
    url = "/api/v1/dashboard?month=2025-05"
    everything = client.get(url, headers=hdr).json()
    banks = [b["bank"] for b in everything["banks"]]
    assert banks, "dashboard must list the banks that have data"
    assert everything["bank"] is None

    parts = [client.get(f"{url}&bank={b}", headers=hdr).json() for b in banks]
    for b, p in zip(banks, parts):
        assert p["bank"] == b
        assert all(t["bank"].lower() == b for t in p["recent_transactions"])
        assert p["banks"] == everything["banks"]          # chips stay stable while filtered
    assert round(sum(p["total_income"] for p in parts), 2) == everything["total_income"]
    assert round(sum(p["total_spent"] for p in parts), 2) == everything["total_spent"]
    assert sum(p["transaction_count"] for p in parts) == everything["transaction_count"]
    if len(banks) > 1:
        assert any(p["total_spent"] != everything["total_spent"] for p in parts)

    # Case-insensitive, and an unknown bank yields an empty (not all-banks) result.
    assert client.get(f"{url}&bank={banks[0].upper()}", headers=hdr).json()["bank"] == banks[0]
    nobody = client.get(f"{url}&bank=nosuchbank", headers=hdr).json()
    assert nobody["transaction_count"] == 0 and nobody["total_spent"] == 0

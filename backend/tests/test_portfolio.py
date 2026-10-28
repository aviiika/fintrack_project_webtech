"""Portfolio CRUD + summary roll-up. Stock prices are mocked (mock_stock_prices
fixture) so gain/loss figures are deterministic."""


def test_add_holding(client, auth_headers):
    r = client.post("/api/v1/portfolio/holdings",
                     json={"symbol": "RELIANCE", "exchange": "NSE",
                           "quantity": 10, "avg_buy_price": 2000.0},
                     headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["symbol"] == "RELIANCE"
    assert body["quantity"] == 10


def test_list_holdings_empty(client, auth_headers):
    r = client.get("/api/v1/portfolio/holdings", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_portfolio_summary_computes_gain_loss(client, auth_headers, mock_stock_prices):
    client.post("/api/v1/portfolio/holdings",
                json={"symbol": "RELIANCE", "quantity": 10, "avg_buy_price": 2000.0},
                headers=auth_headers)
    client.post("/api/v1/portfolio/holdings",
                json={"symbol": "TCS", "quantity": 5, "avg_buy_price": 4000.0},
                headers=auth_headers)

    r = client.get("/api/v1/portfolio/summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()

    assert len(body["holdings"]) == 2
    reliance = next(h for h in body["holdings"] if h["symbol"] == "RELIANCE")
    # mocked price 2500, bought at 2000 * 10 qty -> invested 20000, current 25000, gain 5000
    assert reliance["invested_value"] == 20000.0
    assert reliance["current_value"] == 25000.0
    assert reliance["gain_loss"] == 5000.0
    assert reliance["is_live"] is False  # mocked fallback path

    tcs = next(h for h in body["holdings"] if h["symbol"] == "TCS")
    # mocked price 3800, bought at 4000 * 5 qty -> invested 20000, current 19000, loss -1000
    assert tcs["gain_loss"] == -1000.0

    assert body["total_invested"] == 40000.0
    assert body["total_current_value"] == 44000.0
    assert body["total_gain_loss"] == 4000.0


def test_delete_holding(client, auth_headers):
    created = client.post("/api/v1/portfolio/holdings",
                           json={"symbol": "INFY", "quantity": 3, "avg_buy_price": 1400.0},
                           headers=auth_headers).json()
    r = client.delete(f"/api/v1/portfolio/holdings/{created['id']}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get("/api/v1/portfolio/holdings", headers=auth_headers).json() == []


def test_delete_holding_not_owned_404(client, auth_headers):
    r = client.delete("/api/v1/portfolio/holdings/9999", headers=auth_headers)
    assert r.status_code == 404


def test_portfolio_requires_auth(client):
    r = client.get("/api/v1/portfolio/holdings")
    assert r.status_code == 401

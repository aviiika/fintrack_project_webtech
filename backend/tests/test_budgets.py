def test_budget_crud(client, auth_headers):
    r = client.post("/api/v1/budgets",
                     json={"category":"Food & Dining","monthly_limit":5000,"month":"2025-05"},
                     headers=auth_headers)
    assert r.status_code == 201
    bid = r.json()["id"]
    assert client.get("/api/v1/budgets?month=2025-05", headers=auth_headers).status_code == 200
    assert client.delete(f"/api/v1/budgets/{bid}", headers=auth_headers).status_code == 204

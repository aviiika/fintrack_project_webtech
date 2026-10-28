HDFC = b"""Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/05/25,Zomato Food Order,,01/05/25,450.00,,48500.00
03/05/25,Salary May 2025,,03/05/25,,52000.00,98101.00
"""

def test_import_csv(client, auth_headers):
    r = client.post("/api/v1/import", data={"bank":"hdfc"},
                     files={"file":("test.csv", HDFC, "text/csv")}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["added"] == 2

def test_import_deduplication(client, auth_headers):
    kw = dict(data={"bank":"hdfc"}, files={"file":("t.csv", HDFC, "text/csv")}, headers=auth_headers)
    client.post("/api/v1/import", **kw)
    assert client.post("/api/v1/import", **kw).json()["added"] == 0

def test_import_unknown_bank(client, auth_headers):
    r = client.post("/api/v1/import", data={"bank":"bogus"},
                     files={"file":("t.csv", HDFC, "text/csv")}, headers=auth_headers)
    assert r.status_code == 400

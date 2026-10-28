"""EMI calculation + amortization schedule, exercised both as pure functions and
through the /loans API."""
from datetime import date

from app.models.liability import Liability
from app.services.loan_service import calculate_emi, liability_with_schedule


def test_calculate_emi_known_value():
    # Textbook check: 10,00,000 principal, 10% p.a., 12 months -> EMI ~ 87,916
    emi = calculate_emi(1_000_000, 10.0, 12)
    assert 87_800 <= emi <= 88_000


def test_calculate_emi_zero_interest_is_flat_split():
    emi = calculate_emi(120_000, 0.0, 12)
    assert emi == 10_000.0


def test_liability_schedule_fresh_loan_has_full_balance():
    l = Liability(id=1, name="Car Loan", liability_type="car_loan",
                   principal_amount=500_000, interest_rate_annual=9.0, tenure_months=36,
                   emi_amount=calculate_emi(500_000, 9.0, 36),
                   start_date=date.today().isoformat(), owner_id=1)  # noqa: DTZ011
    schedule = liability_with_schedule(l)
    assert schedule["months_elapsed"] == 0
    assert schedule["months_remaining"] == 36
    assert schedule["outstanding_balance"] == 500_000.0


def test_liability_schedule_partially_paid_loan_reduces_balance():
    emi = calculate_emi(500_000, 9.0, 36)
    l = Liability(id=1, name="Car Loan", liability_type="car_loan",
                   principal_amount=500_000, interest_rate_annual=9.0, tenure_months=36,
                   emi_amount=emi, start_date="2024-01-01", owner_id=1)
    schedule = liability_with_schedule(l)
    assert schedule["months_elapsed"] > 0
    assert schedule["outstanding_balance"] < 500_000.0
    assert schedule["total_paid_so_far"] == round(emi * schedule["months_elapsed"], 2)


def test_create_and_list_loan_via_api(client, auth_headers):
    r = client.post("/api/v1/loans", json={
        "name": "Home Loan", "liability_type": "home_loan",
        "principal_amount": 2_500_000, "interest_rate_annual": 8.5,
        "tenure_months": 240, "start_date": "2023-06-01",
    }, headers=auth_headers)
    assert r.status_code == 201
    created = r.json()
    assert created["emi_amount"] > 0

    r = client.get("/api/v1/loans", headers=auth_headers)
    assert r.status_code == 200
    loans = r.json()
    assert len(loans) == 1
    assert loans[0]["outstanding_balance"] < loans[0]["principal_amount"]


def test_delete_loan_not_owned_404(client, auth_headers):
    r = client.delete("/api/v1/loans/9999", headers=auth_headers)
    assert r.status_code == 404

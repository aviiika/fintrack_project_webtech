import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app


@pytest.fixture
def ml_tmpdir(monkeypatch):
    """Isolated ML models dir per test — prevents cross-test contamination.
    Also lowers the min-training-sample threshold so tests can train on ~30 rows
    (production default is 50)."""
    d = Path(tempfile.mkdtemp(prefix="fintrack_ml_"))
    from app.config import settings
    monkeypatch.setattr(settings, "ml_models_dir", str(d))
    monkeypatch.setattr(settings, "ml_min_training_samples", 20)
    # Clear inference cache before each test
    from app.ml.inference import categoriser_service
    categoriser_service._load_model.cache_clear()
    yield d
    shutil.rmtree(d, ignore_errors=True)
    categoriser_service._load_model.cache_clear()

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """The login rate limiter is a process-wide singleton keyed by client IP, and
    every test hits it from the same 'testclient' IP. Without this reset, the
    auth_headers fixture (which registers a user per test) exhausts the window
    after 10 tests and every later test fails with 429 -- a test-isolation
    problem, not a bug in the limiter. test_security.py asserts it really blocks.
    """
    from app.utils.security_middleware import login_limiter
    login_limiter.reset()
    yield
    login_limiter.reset()

@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SM = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    s = SM()
    try: yield s
    finally: s.close(); Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session, ml_tmpdir, monkeypatch):
    # Background scheduler and live network calls have no place in a test run:
    # the scheduler needs a long-lived asyncio loop TestClient doesn't provide,
    # and stock prices must be deterministic for assertions to be meaningful.
    from app.config import settings
    monkeypatch.setattr(settings, "enable_background_jobs", False)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "t@f.app", "full_name": "Test", "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

@pytest.fixture
def mock_stock_prices(monkeypatch):
    """Deterministic, offline stock prices for portfolio/net-worth tests.

    Avoids depending on yfinance/network inside the test suite; the real fallback
    path (stock_service._mock_price) is already exercised implicitly whenever the
    live fetch fails, so this just pins the numbers for stable assertions.
    """
    from app.services import stock_service

    fixed = {"RELIANCE": 2500.0, "TCS": 3800.0, "INFY": 1500.0}

    def _fake_get_price(symbol):
        symbol = symbol.upper().strip()
        price = fixed.get(symbol, 1000.0)
        return {"symbol": symbol, "price": price, "previous_close": price,
                "is_live": False, "fetched_at": "2026-01-01T00:00:00+00:00"}

    def _fake_get_prices(symbols):
        return {s.upper().strip(): _fake_get_price(s) for s in symbols}

    monkeypatch.setattr(stock_service, "get_price", _fake_get_price)
    monkeypatch.setattr(stock_service, "get_prices", _fake_get_prices)
    # portfolio_service and the routes import get_prices directly into their module
    # namespace, so patch those references too.
    from app.services import portfolio_service
    monkeypatch.setattr(portfolio_service, "get_prices", _fake_get_prices)
    from app.routes import portfolio as portfolio_routes
    monkeypatch.setattr(portfolio_routes, "get_prices", _fake_get_prices)
    return fixed


@pytest.fixture
def seeded_client(client, auth_headers):
    """Client with ~30 transactions loaded, enough for ML training."""
    csv = b"""Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/05/25,Zomato Food Order,,01/05/25,450.00,,48500.00
02/05/25,Swiggy Lunch,,02/05/25,320.00,,48180.00
03/05/25,Zomato Breakfast,,03/05/25,210.00,,47970.00
04/05/25,Swiggy Dinner,,04/05/25,680.00,,47290.00
05/05/25,Restaurant Dinner,,05/05/25,1200.00,,46090.00
06/05/25,BigBasket Groceries,,06/05/25,1850.00,,44240.00
07/05/25,Reliance Fresh Grocery,,07/05/25,920.00,,43320.00
08/05/25,Blinkit Groceries,,08/05/25,760.00,,42560.00
09/05/25,Zepto Groceries,,09/05/25,540.00,,42020.00
10/05/25,Ola Cab Booking,,10/05/25,180.00,,41840.00
11/05/25,Uber Ride,,11/05/25,220.00,,41620.00
12/05/25,Petrol Pump Payment,,12/05/25,1500.00,,40120.00
13/05/25,Rapido Bike Taxi,,13/05/25,95.00,,40025.00
14/05/25,IRCTC Train Ticket,,14/05/25,1240.00,,38785.00
15/05/25,JIO Prepaid Recharge,,15/05/25,299.00,,38486.00
16/05/25,Airtel Broadband,,16/05/25,799.00,,37687.00
17/05/25,BESCOM Electricity Bill,,17/05/25,1200.00,,36487.00
18/05/25,Netflix Subscription,,18/05/25,649.00,,35838.00
19/05/25,Spotify Premium,,19/05/25,119.00,,35719.00
20/05/25,Amazon Prime Annual,,20/05/25,1499.00,,34220.00
21/05/25,Amazon Shopping,,21/05/25,2399.00,,31821.00
22/05/25,Myntra Clothing,,22/05/25,1799.00,,30022.00
23/05/25,Flipkart Order,,23/05/25,999.00,,29023.00
24/05/25,Apollo Pharmacy,,24/05/25,540.00,,28483.00
25/05/25,1mg Medicine Order,,25/05/25,680.00,,27803.00
26/05/25,Udemy Course Purchase,,26/05/25,499.00,,27304.00
27/05/25,House Rent Payment,,27/05/25,12000.00,,15304.00
28/05/25,Groww SIP Investment,,28/05/25,5000.00,,10304.00
29/05/25,Zerodha Mutual Fund,,29/05/25,3000.00,,7304.00
30/05/25,Salary May 2025,,30/05/25,,52000.00,59304.00
31/05/25,Freelance Payment Received,,31/05/25,,8000.00,67304.00
"""
    client.post("/api/v1/import", data={"bank": "hdfc"},
                files={"file": ("seed.csv", csv, "text/csv")}, headers=auth_headers)
    return client, auth_headers

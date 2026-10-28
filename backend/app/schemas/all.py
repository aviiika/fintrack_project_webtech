"""All Pydantic schemas in one module (simpler imports)."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; email: str; full_name: str; is_active: bool; created_at: datetime

class LoginRequest(BaseModel):
    email: str; password: str

class Token(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserRead


# ── Transactions ─────────────────────────────────────────────────────────────
class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; date: str; description: str; amount: float; txn_type: str
    category: str | None; bank: str; source_file: str | None; balance: float | None
    category_source: str | None = None
    category_confidence: float | None = None
    user_corrected: bool = False
    owner_id: int; created_at: datetime

class TransactionUpdate(BaseModel):
    category: str | None = None
    description: str | None = None

class TransactionListResponse(BaseModel):
    total: int
    items: list[TransactionRead]


# ── Budgets ──────────────────────────────────────────────────────────────────
class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float = Field(gt=0)
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")

class BudgetUpdate(BaseModel):
    monthly_limit: float | None = Field(default=None, gt=0)
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")

class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; category: str; month: str | None; monthly_limit: float; owner_id: int

class BudgetWithSpending(BaseModel):
    id: int; category: str; month: str | None; monthly_limit: float
    spent: float; remaining: float; percent_used: float
    over_budget: bool; status: str


# ── Import logs ──────────────────────────────────────────────────────────────
class ImportLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; filename: str; bank: str
    rows_parsed: int; rows_added: int; imported_at: datetime


# ── ML (NEW) ─────────────────────────────────────────────────────────────────
class CategoryPrediction(BaseModel):
    """What the ML categoriser returns for a single description."""
    category: str
    source: str       # 'ml' | 'rules_low_confidence' | 'rules_no_model'
    confidence: float | None = None
    rules_fallback_reason: str | None = None

class ModelInfo(BaseModel):
    """Metadata about the currently active model."""
    status: str                          # 'active' | 'no_model_trained'
    using: str                           # 'ml_with_fallback' | 'keyword_rules'
    active_model_path: str | None = None
    accuracy: float | None = None
    trained_on_samples: int | None = None
    trained_at: datetime | None = None
    classes: list[str] | None = None
    per_class_f1: dict[str, float] | None = None
    confusion_matrix: dict | None = None

class RetrainResult(BaseModel):
    status: str          # 'trained' | 'insufficient_data' | 'error'
    message: str
    model_info: ModelInfo | None = None

class PredictionRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    txn_type: str = Field(default="debit", pattern=r"^(debit|credit)$")

class AnomalyFlag(BaseModel):
    id: int; description: str; amount: float; date: str
    typical_amount: float; times_above_average: float; z_score: float

class SpendForecast(BaseModel):
    days_elapsed: int; days_in_month: int
    spent_so_far: float
    daily_rate: float | None = None
    projected_month_end: float | None = None
    projected_overspend: float | None = None

class CorrectionStatus(BaseModel):
    corrections_this_cycle: int
    threshold_for_retrain: int
    total_lifetime_corrections: int
    next_retrain_in: int


# ── Portfolio (NEW, Week 2) ───────────────────────────────────────────────────
class StockHoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")
    quantity: float = Field(gt=0)
    avg_buy_price: float = Field(gt=0)

class StockHoldingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; symbol: str; exchange: str; quantity: float; avg_buy_price: float
    owner_id: int; created_at: datetime

class HoldingSummary(BaseModel):
    id: int; symbol: str; exchange: str; quantity: float; avg_buy_price: float
    current_price: float; is_live: bool
    invested_value: float; current_value: float
    gain_loss: float; gain_loss_pct: float

class PortfolioSummary(BaseModel):
    holdings: list[HoldingSummary]
    total_invested: float
    total_current_value: float
    total_gain_loss: float
    total_gain_loss_pct: float

class LivePriceTick(BaseModel):
    symbol: str; price: float; previous_close: float; is_live: bool; fetched_at: str


# ── Loans / liabilities (NEW, Week 3) ─────────────────────────────────────────
class LiabilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    liability_type: str = Field(pattern=r"^(home_loan|car_loan|personal_loan|education_loan|credit_card|other)$")
    principal_amount: float = Field(gt=0)
    interest_rate_annual: float = Field(ge=0, le=50)
    tenure_months: int = Field(gt=0, le=480)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

class LiabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; liability_type: str
    principal_amount: float; interest_rate_annual: float; tenure_months: int
    emi_amount: float; start_date: str; owner_id: int; created_at: datetime

class LiabilityWithSchedule(BaseModel):
    id: int; name: str; liability_type: str
    principal_amount: float; interest_rate_annual: float; tenure_months: int
    emi_amount: float; start_date: str
    months_elapsed: int; months_remaining: int
    outstanding_balance: float; total_interest_payable: float; total_paid_so_far: float


# ── Net worth (NEW, Week 3) ───────────────────────────────────────────────────
class NetWorthSummary(BaseModel):
    cash_balance: float
    investments_value: float
    total_assets: float
    total_liabilities: float
    net_worth: float
    liabilities: list[LiabilityWithSchedule]

class NetWorthHistoryPoint(BaseModel):
    date: str; net_worth: float; total_assets: float; total_liabilities: float

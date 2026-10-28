from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Liability(Base):
    """A loan / debt (home loan, car loan, credit card, etc).

    Only the immutable terms are stored (principal, rate, tenure, start date) plus the
    computed EMI. Outstanding balance is deliberately NOT stored as a column -- it's derived
    on read from the reducing-balance formula in loan_service, so it can never drift out of
    sync with the terms (no "update outstanding every month" job to forget to run).
    """
    __tablename__ = "liabilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    liability_type: Mapped[str] = mapped_column(String(32), index=True)
    principal_amount: Mapped[float] = mapped_column(Float)
    interest_rate_annual: Mapped[float] = mapped_column(Float)
    tenure_months: Mapped[int] = mapped_column(Integer)
    emi_amount: Mapped[float] = mapped_column(Float)
    start_date: Mapped[str] = mapped_column(String(10))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(UTC))
    owner: Mapped["User"] = relationship(back_populates="liabilities")  # noqa: F821

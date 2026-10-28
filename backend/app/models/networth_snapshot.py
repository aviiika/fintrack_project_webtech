from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class NetWorthSnapshot(Base):
    """One point-in-time net worth reading, taken daily by the background scheduler
    (app/background/scheduler.py:nightly_networth_snapshot) so /networth/history has a
    real time series to chart instead of only ever showing "now"."""
    __tablename__ = "networth_snapshots"
    __table_args__ = (UniqueConstraint("owner_id", "date", name="uq_networth_owner_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    total_assets: Mapped[float] = mapped_column(Float)
    total_liabilities: Mapped[float] = mapped_column(Float)
    net_worth: Mapped[float] = mapped_column(Float)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(UTC))
    owner: Mapped["User"] = relationship(back_populates="networth_snapshots")  # noqa: F821

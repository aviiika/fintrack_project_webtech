from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class StockHolding(Base):
    """A user's position in one listed stock (quantity + average buy price).

    Current price is never stored here -- it's fetched live (and cached) through
    stock_service, so this table only holds what the user actually told us.
    """
    __tablename__ = "stock_holdings"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    quantity: Mapped[float] = mapped_column(Float)
    avg_buy_price: Mapped[float] = mapped_column(Float)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(UTC))
    owner: Mapped["User"] = relationship(back_populates="stock_holdings")  # noqa: F821

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float)
    txn_type: Mapped[str] = mapped_column(String(10))
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    bank: Mapped[str] = mapped_column(String(50), index=True)
    source_file: Mapped[str | None] = mapped_column(String(255))
    balance: Mapped[float | None] = mapped_column(Float)
    # NEW: tracks how the category was assigned (rules vs ML, with confidence)
    category_source: Mapped[str | None] = mapped_column(String(32))  # 'rules'|'ml'|'manual'
    category_confidence: Mapped[float | None] = mapped_column(Float)
    user_corrected: Mapped[bool] = mapped_column(default=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    owner: Mapped["User"] = relationship(back_populates="transactions")  # noqa: F821

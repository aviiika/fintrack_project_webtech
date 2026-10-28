from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100))
    month: Mapped[str | None] = mapped_column(String(7), index=True)
    monthly_limit: Mapped[float] = mapped_column(Float)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    owner: Mapped["User"] = relationship(back_populates="budgets")  # noqa: F821

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base

class CorrectionCounter(Base):
    """Per-user counter — increments each time a user corrects an ML category.
    When it hits ml_retrain_every_n_corrections, retraining is triggered."""
    __tablename__ = "correction_counters"
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    total_lifetime_corrections: Mapped[int] = mapped_column(Integer, default=0)

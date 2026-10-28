from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

class ImportLog(Base):
    __tablename__ = "import_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    bank: Mapped[str] = mapped_column(String(50))
    rows_parsed: Mapped[int] = mapped_column(Integer, default=0)
    rows_added: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   default=lambda: datetime.now(timezone.utc))
    owner: Mapped["User"] = relationship(back_populates="imports")  # noqa: F821

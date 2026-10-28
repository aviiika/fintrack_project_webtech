from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # noqa: F821
    budgets: Mapped[list["Budget"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # noqa: F821
    imports: Mapped[list["ImportLog"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # noqa: F821
    stock_holdings: Mapped[list["StockHolding"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # noqa: F821
    liabilities: Mapped[list["Liability"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # noqa: F821
    networth_snapshots: Mapped[list["NetWorthSnapshot"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # noqa: F821

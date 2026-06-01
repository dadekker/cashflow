from sqlalchemy import Boolean, Date, DateTime, Float, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .database import Base

class Anchor(Base):
    __tablename__ = "anchors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

class Cashflow(Base):
    __tablename__ = "cashflows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(12))
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_date: Mapped[str] = mapped_column(String(10), index=True)
    end_type: Mapped[str] = mapped_column(String(20), default="never")
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Holding(Base):
    __tablename__ = "holdings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    shares: Mapped[float] = mapped_column(Float)
    cost_per_share: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    opened_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

class PriceCache(Base):
    __tablename__ = "price_cache"
    ticker: Mapped[str] = mapped_column(String(32), primary_key=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    as_of: Mapped[datetime] = mapped_column(DateTime)

class FxCache(Base):
    __tablename__ = "fx_cache"
    pair: Mapped[str] = mapped_column(String(6), primary_key=True)
    rate: Mapped[float] = mapped_column(Float)
    as_of: Mapped[datetime] = mapped_column(DateTime)

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    id: Mapped[str] = mapped_column(String(512), primary_key=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    challenge: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

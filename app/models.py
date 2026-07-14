"""SQLAlchemy ORM models."""
from sqlalchemy import Column, DateTime, Float, String

from app.database.postgres import Base


class Token(Base):
    """Latest best bid/ask for a given (exchange, symbol) pair."""

    __tablename__ = "tokens"

    exchange = Column(String, primary_key=True)
    symbol = Column(String, primary_key=True)

    ask = Column(Float)
    askQ = Column(Float)

    bid = Column(Float)
    bidQ = Column(Float)

    ts = Column(DateTime)


class SpreadOpportunity(Base):
    """A cross-exchange arbitrage opportunity above the configured threshold."""

    __tablename__ = "spread_opportunities"

    id = Column(String, primary_key=True)
    symbol = Column(String, index=True)

    buy_exchange = Column(String)
    buy_price = Column(Float)

    sell_exchange = Column(String)
    sell_price = Column(Float)

    spread_pct = Column(Float)

    ts = Column(DateTime)

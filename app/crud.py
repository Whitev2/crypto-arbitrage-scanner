"""Persistence helpers for market data and detected opportunities."""
import datetime
import logging
import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.postgres import postgres
from app.models import SpreadOpportunity, Token

logger = logging.getLogger(__name__)


class TokenCrud:
    @staticmethod
    async def update_token_data(
        exchange: str,
        symbol: str,
        ask: float,
        askQ: float,
        bid: float,
        bidQ: float,
        ts: float,
    ) -> None:
        """Upsert the latest best bid/ask for an (exchange, symbol) pair.

        Uses a real PostgreSQL ``INSERT ... ON CONFLICT DO UPDATE`` keyed on the
        ``(exchange, symbol)`` composite primary key. This is the correct async
        SQLAlchemy 1.4 pattern: ``AsyncSession.merge`` requires a fully loaded
        identity and issues an extra SELECT per call, whereas an upsert
        statement is a single round-trip and is safe under concurrency.
        """
        values = {
            "exchange": exchange,
            "symbol": symbol,
            "ask": float(ask),
            "askQ": float(askQ),
            "bid": float(bid),
            "bidQ": float(bidQ),
            "ts": datetime.datetime.fromtimestamp(ts),
        }

        stmt = pg_insert(Token).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Token.exchange, Token.symbol],
            set_={
                "ask": stmt.excluded.ask,
                "askQ": stmt.excluded.askQ,
                "bid": stmt.excluded.bid,
                "bidQ": stmt.excluded.bidQ,
                "ts": stmt.excluded.ts,
            },
        )

        async with postgres.async_session() as session:
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def save_opportunity(
        symbol: str,
        buy_exchange: str,
        buy_price: float,
        sell_exchange: str,
        sell_price: float,
        spread_pct: float,
    ) -> None:
        """Persist a cross-exchange arbitrage opportunity."""
        opportunity = SpreadOpportunity(
            id=str(uuid.uuid4()),
            symbol=symbol,
            buy_exchange=buy_exchange,
            buy_price=float(buy_price),
            sell_exchange=sell_exchange,
            sell_price=float(sell_price),
            spread_pct=float(spread_pct),
            ts=datetime.datetime.utcnow(),
        )

        async with postgres.async_session() as session:
            session.add(opportunity)
            await session.commit()


token_crud = TokenCrud()

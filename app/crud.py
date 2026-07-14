"""Persistence helpers for market data and detected opportunities."""
import datetime
import uuid

from app.database.postgres import postgres
from app.models import SpreadOpportunity, Token


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
        """Upsert the latest best bid/ask for an (exchange, symbol) pair."""
        token = Token(
            exchange=exchange,
            symbol=symbol,
            ask=float(ask),
            askQ=float(askQ),
            bid=float(bid),
            bidQ=float(bidQ),
            ts=datetime.datetime.fromtimestamp(ts),
        )

        async with postgres.async_session() as session:
            # merge() performs an upsert on the composite primary key.
            await session.merge(token)
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

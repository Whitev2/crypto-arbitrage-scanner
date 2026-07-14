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
        # upsert по (exchange, symbol) — один round-trip, safe под конкуренцией
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

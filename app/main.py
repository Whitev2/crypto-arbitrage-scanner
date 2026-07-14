"""Entry point: connect to every exchange feed and stream quotes concurrently.

Each exchange client runs as an independent asyncio task. Incoming quotes are
persisted by the CRUD layer, and the spread calculator turns the aggregated
book into cross-exchange arbitrage opportunities.
"""
import asyncio

from app.database.postgres import Postgres
from app.database.redis import RedisCache
from app.sockets.binance.ws import run_binance
from app.sockets.gateio.ws import run_gateio
from app.sockets.huobi.ws import run_huobi
from app.sockets.okx.ws import run_okx


async def main() -> None:
    Postgres.connect_to_storage()
    await RedisCache.connect_to_storage()

    await asyncio.gather(
        run_binance(),
        run_okx(),
        run_huobi(),
        run_gateio(),
    )


if __name__ == "__main__":
    asyncio.run(main())

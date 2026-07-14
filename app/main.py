"""Entry point: connect to every exchange feed and stream quotes concurrently.

Each exchange client runs as an independent, supervised asyncio task. A crash
in one exchange feed must never take the others down, so every client is
wrapped in a supervisor that logs the failure and restarts it. Incoming quotes
are persisted by the CRUD layer, and the spread calculator turns the aggregated
book into cross-exchange arbitrage opportunities.
"""
import asyncio
import logging

from app.database.postgres import Postgres
from app.database.redis import RedisCache
from app.sockets.binance.ws import run_binance
from app.sockets.gateio.ws import run_gateio
from app.sockets.huobi.ws import run_huobi
from app.sockets.okx.ws import run_okx

logger = logging.getLogger(__name__)

# How long to wait before restarting a supervised exchange task that returned
# or raised. Kept small so a transient failure recovers quickly.
RESTART_DELAY = 5.0


async def supervise(name, factory) -> None:
    """Run ``factory()`` forever, restarting (with logging) if it ever exits.

    The individual clients already reconnect internally, so reaching this
    handler means something unexpected happened; we still refuse to let a
    single exchange bring down the process.
    """
    while True:
        try:
            await factory()
            logger.warning("%s task exited unexpectedly, restarting", name)
        except asyncio.CancelledError:
            logger.info("%s supervisor cancelled", name)
            raise
        except Exception:  # noqa: BLE001 - one exchange must not kill the rest
            logger.exception("%s task crashed, restarting", name)
        await asyncio.sleep(RESTART_DELAY)


async def main() -> None:
    Postgres.connect_to_storage()
    await RedisCache.connect_to_storage()

    tasks = {
        "binance": run_binance,
        "okx": run_okx,
        "huobi": run_huobi,
        "gateio": run_gateio,
    }

    # return_exceptions=True is a belt-and-braces guard: each task is already
    # individually supervised, so gather should never see one propagate.
    await asyncio.gather(
        *(supervise(name, factory) for name, factory in tasks.items()),
        return_exceptions=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

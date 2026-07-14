import asyncio
import logging

from app.database.postgres import Postgres
from app.database.redis import RedisCache
from app.sockets.binance.ws import run_binance
from app.sockets.gateio.ws import run_gateio
from app.sockets.huobi.ws import run_huobi
from app.sockets.okx.ws import run_okx

logger = logging.getLogger(__name__)

RESTART_DELAY = 5.0


async def supervise(name, factory) -> None:
    # одна биржа не должна ронять остальные — рестартим с логом
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

    # каждая таска уже под supervise, return_exceptions на всякий
    await asyncio.gather(
        *(supervise(name, factory) for name, factory in tasks.items()),
        return_exceptions=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

import asyncio
import logging
from typing import Awaitable, Callable

import websockets

logger = logging.getLogger(__name__)

INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0
BACKOFF_FACTOR = 2.0

# нет данных за timeout -> считаем стрим мёртвым, реконнект
DEFAULT_READ_TIMEOUT = 30.0


async def recv_with_timeout(websocket, timeout: float = DEFAULT_READ_TIMEOUT):
    return await asyncio.wait_for(websocket.recv(), timeout=timeout)


async def run_socket_forever(
    name: str,
    connect: Callable[[], Awaitable[None]],
    subscribe: Callable[[], Awaitable[None]],
    consume: Callable[[], Awaitable[None]],
    *,
    read_timeout: float = DEFAULT_READ_TIMEOUT,
    max_backoff: float = MAX_BACKOFF,
) -> None:
    # reconnect + экспоненциальный backoff, сброс после успешного коннекта
    backoff = INITIAL_BACKOFF
    while True:
        try:
            await connect()
            await subscribe()
            backoff = INITIAL_BACKOFF
            logger.info("%s: connected", name)
            await consume()
            logger.warning("%s: stream closed, reconnecting", name)
        except asyncio.CancelledError:
            logger.info("%s: cancelled, shutting down", name)
            raise
        except asyncio.TimeoutError:
            logger.warning(
                "%s: no data within %.0fs, reconnecting", name, read_timeout
            )
        except websockets.ConnectionClosed:
            logger.warning("%s: connection closed, reconnecting", name)
        except Exception:  # noqa: BLE001 - keep the task alive on any error
            logger.exception("%s: unexpected error, reconnecting", name)

        await asyncio.sleep(backoff)
        backoff = min(backoff * BACKOFF_FACTOR, max_backoff)

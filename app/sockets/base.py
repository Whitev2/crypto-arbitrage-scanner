"""Shared WebSocket resilience helpers.

Every exchange client needs the same production-grade behaviour:

* automatically reconnect when the stream drops (``ConnectionClosed`` or any
  other network error) instead of crashing the task,
* back off exponentially between attempts (capped) so we do not hammer a
  struggling endpoint, and
* apply a read timeout so a silently dead connection is detected and recycled
  rather than hanging forever.

``run_socket_forever`` factors that loop out so each client only has to supply
three small coroutines: connect, (re)subscribe, and consume one message.
"""
import asyncio
import logging
from typing import Awaitable, Callable

import websockets

logger = logging.getLogger(__name__)

# Reconnect backoff bounds (seconds).
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0
BACKOFF_FACTOR = 2.0

# If no message arrives within this many seconds, treat the stream as dead,
# drop it and reconnect (guards against silently stalled connections).
DEFAULT_READ_TIMEOUT = 30.0


async def recv_with_timeout(websocket, timeout: float = DEFAULT_READ_TIMEOUT):
    """Receive a single message, raising ``asyncio.TimeoutError`` if the stream
    stays silent for longer than ``timeout`` seconds."""
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
    """Run a WebSocket client forever with reconnect + exponential backoff.

    Parameters
    ----------
    name:
        Human-readable exchange name, used for logging.
    connect:
        Coroutine that establishes (or re-establishes) the connection.
    subscribe:
        Coroutine that sends any subscription messages after connecting.
    consume:
        Coroutine that reads and processes messages until the stream closes.
        It is expected to loop internally and to honour ``read_timeout`` via
        :func:`recv_with_timeout`.
    """
    backoff = INITIAL_BACKOFF
    while True:
        try:
            await connect()
            await subscribe()
            # Successful (re)connection: reset the backoff.
            backoff = INITIAL_BACKOFF
            logger.info("%s: connected", name)
            await consume()
            # ``consume`` returned without raising: the stream closed cleanly.
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

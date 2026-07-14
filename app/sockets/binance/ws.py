"""Binance spot WebSocket client (best bid/ask + rolling ticker)."""
import asyncio
import json
import logging

import websockets

from app.sockets.base import DEFAULT_READ_TIMEOUT, recv_with_timeout, run_socket_forever
from app.sockets.binance.symbols import binance_symbols

logger = logging.getLogger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="


def build_stream_url(symbols: list[str]) -> str:
    """Build a combined-stream URL for bookTicker + ticker of every symbol."""
    streams = []
    for symbol in symbols:
        stream_symbol = symbol.replace("-", "").lower()
        streams.append(f"{stream_symbol}@bookTicker")
        streams.append(f"{stream_symbol}@ticker")
    return BINANCE_WS_BASE + "/".join(streams)


class BinanceSocket:
    def __init__(self, symbols: list[str] | None = None):
        self.symbols = symbols or binance_symbols
        self.websocket = None

    async def connect(self) -> None:
        self.websocket = await websockets.connect(build_stream_url(self.symbols))

    async def subscribe(self) -> None:
        # Binance subscribes via the combined-stream URL, so nothing to send.
        return None

    def handle_message(self, message: str) -> None:
        stream = json.loads(message)

        stream_name = stream.get("stream", "")
        data = stream.get("data", {})
        symbol = data.get("s")

        if "bookTicker" in stream_name:
            ask = data.get("a")
            ask_q = data.get("A")

            bid = data.get("b")
            bid_q = data.get("B")

            logger.info(
                "BINANCE | %s | ASK: %s | ASKQ: %s | BID: %s | BIDQ: %s",
                symbol, ask, ask_q, bid, bid_q,
            )
        elif "ticker" in stream_name:
            token_volume = data.get("v")
            usdt_volume = data.get("q")
            logger.info(
                "BINANCE | %s | TOKEN_VOLUME: %s | USDT_VOLUME: %s",
                symbol, token_volume, usdt_volume,
            )

    async def view_messages(self) -> None:
        while True:
            message = await recv_with_timeout(self.websocket, DEFAULT_READ_TIMEOUT)
            self.handle_message(message)


async def run_binance() -> None:
    socket = BinanceSocket()
    await run_socket_forever(
        "BINANCE",
        connect=socket.connect,
        subscribe=socket.subscribe,
        consume=socket.view_messages,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_binance())

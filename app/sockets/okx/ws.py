"""OKX spot WebSocket client (order-book top-5 + ticker)."""
import asyncio
import json
import logging

import websockets

from app.sockets.base import DEFAULT_READ_TIMEOUT, recv_with_timeout, run_socket_forever
from app.sockets.okx.symbols import okx_symbols

logger = logging.getLogger(__name__)

OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"


class OKXSocket:
    def __init__(self, symbols: list[str] | None = None):
        self.symbols = symbols or okx_symbols
        self.websocket = None

    async def connect(self) -> None:
        self.websocket = await websockets.connect(OKX_WS_URL)

    async def _subscribe(self, channel: str, pair: str) -> None:
        params = {"op": "subscribe", "args": [{"channel": channel, "instId": pair}]}
        await self.websocket.send(json.dumps(params))

    async def sub_ticker(self, pair: str) -> None:
        await self._subscribe("tickers", pair)

    async def sub_book(self, pair: str) -> None:
        await self._subscribe("books5", pair)

    async def subscribe(self) -> None:
        for symbol in self.symbols:
            await self.sub_book(symbol)
            await self.sub_ticker(symbol)

    def handle_message(self, message: str) -> None:
        stream = json.loads(message)
        stream_name = stream.get("arg", {}).get("channel", "")
        data = stream.get("data", [None])[0]
        if data is None:
            return

        symbol = data.get("instId")

        if "books" in stream_name:
            ask, ask_q = data["asks"][0][0], data["asks"][0][1]
            bid, bid_q = data["bids"][0][0], data["bids"][0][1]
            logger.info(
                "OKX | %s | ASK: %s | ASKQ: %s | BID: %s | BIDQ: %s",
                symbol, ask, ask_q, bid, bid_q,
            )
        elif "tickers" in stream_name:
            token_volume = data.get("vol24h")
            usdt_volume = data.get("volCcy24h")
            logger.info(
                "OKX | %s | TOKEN_VOLUME: %s | USDT_VOLUME: %s",
                symbol, token_volume, usdt_volume,
            )

    async def view_messages(self) -> None:
        while True:
            message = await recv_with_timeout(self.websocket, DEFAULT_READ_TIMEOUT)
            self.handle_message(message)


async def run_okx() -> None:
    socket = OKXSocket()
    await run_socket_forever(
        "OKX",
        connect=socket.connect,
        subscribe=socket.subscribe,
        consume=socket.view_messages,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_okx())

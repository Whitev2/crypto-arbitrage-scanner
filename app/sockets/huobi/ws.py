"""Huobi (HTX) spot WebSocket client (ticker channel, gzip framed)."""
import asyncio
import gzip
import json
import logging

import websockets

from app.sockets.base import DEFAULT_READ_TIMEOUT, recv_with_timeout, run_socket_forever
from app.sockets.huobi.symbols import huobi_symbols

logger = logging.getLogger(__name__)

HUOBI_WS_URL = "wss://api.huobi.pro/ws"


class HuobiSocket:
    def __init__(self, symbols: list[str] | None = None):
        self.symbols = symbols or huobi_symbols
        self.websocket = None

    async def connect(self) -> None:
        self.websocket = await websockets.connect(HUOBI_WS_URL)

    async def sub_ticker(self, pair: str) -> None:
        params = {"sub": f"market.{pair.lower().replace('-', '')}.ticker"}
        await self.websocket.send(json.dumps(params))

    async def subscribe(self) -> None:
        for symbol in self.symbols:
            await self.sub_ticker(symbol)

    async def handle_message(self, message) -> None:
        if isinstance(message, bytes):
            message = gzip.decompress(message)

        stream = json.loads(message)

        # Huobi requires a pong reply to keep the connection alive.
        if stream.get("ping"):
            await self.websocket.send(json.dumps({"pong": stream["ping"]}))
            return

        stream_name = stream.get("ch", "")
        data = stream.get("tick")

        if "ticker" in stream_name and data:
            ask = data.get("ask")
            ask_q = data.get("askSize")

            bid = data.get("bid")
            bid_q = data.get("bidSize")

            symbol = stream_name.split(".")[1].upper()
            usdt_volume = data.get("vol")
            logger.info(
                "HUOBI | %s | ASK: %s | ASKQ: %s | BID: %s | BIDQ: %s | USDT_VOLUME: %s",
                symbol, ask, ask_q, bid, bid_q, usdt_volume,
            )

    async def view_messages(self) -> None:
        while True:
            message = await recv_with_timeout(self.websocket, DEFAULT_READ_TIMEOUT)
            await self.handle_message(message)


async def run_huobi() -> None:
    socket = HuobiSocket()
    await run_socket_forever(
        "HUOBI",
        connect=socket.connect,
        subscribe=socket.subscribe,
        consume=socket.view_messages,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_huobi())

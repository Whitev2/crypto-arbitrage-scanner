import asyncio
import json
import logging
import time
from typing import List, Optional

import aiohttp
import websockets

from app.sockets.base import DEFAULT_READ_TIMEOUT, recv_with_timeout, run_socket_forever
from app.sockets.gateio.symbols import gateio_symbols

logger = logging.getLogger(__name__)

GATEIO_WS_URL = "wss://api.gateio.ws/ws/v4/"
GATEIO_PAIRS_URL = "https://api.gateio.ws/api/v4/spot/currency_pairs"


class GateioSocket:
    def __init__(self, symbols: Optional[List[str]] = None):
        self.symbols = symbols or gateio_symbols
        self.websocket = None
        self.pairs: Optional[List] = None
        self.last_time = time.time()

    async def connect(self) -> None:
        if self.pairs is None:
            await self.load_currency_pairs()
        self.websocket = await websockets.connect(GATEIO_WS_URL)

    async def load_currency_pairs(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(GATEIO_PAIRS_URL) as resp:
                self.pairs = await resp.json()

    def _normalize(self, pairs: Optional[List[str]]) -> List[str]:
        if pairs is None:
            return [pair.get("id") for pair in (self.pairs or [])]
        return [pair.replace("-", "_") for pair in pairs]

    async def sub_ticker(self, pairs: Optional[List[str]] = None) -> None:
        for pair in self._normalize(pairs):
            params = {
                "time": int(time.time()),
                "channel": "spot.tickers",
                "event": "subscribe",
                "payload": [pair],
            }
            await self.websocket.send(json.dumps(params))

    async def sub_book(self, pairs: Optional[List[str]] = None) -> None:
        params = {
            "time": int(time.time()),
            "channel": "spot.book_ticker",
            "event": "subscribe",
            "payload": self._normalize(pairs),
        }
        await self.websocket.send(json.dumps(params))

    async def subscribe(self) -> None:
        await self.sub_book(pairs=self.symbols)

    def handle_message(self, message: str) -> None:
        stream = json.loads(message)
        stream_name = stream.get("channel")
        data = stream.get("result")

        if data is None or stream.get("event") != "update":
            return

        if "book_ticker" in stream_name:
            symbol = data.get("s")
            ask, ask_q = data.get("a"), data.get("A")
            bid, bid_q = data.get("b"), data.get("B")
            logger.info(
                "GATE.IO | %s | ASK: %s | ASKQ: %s | BID: %s | BIDQ: %s",
                symbol, ask, ask_q, bid, bid_q,
            )
        elif stream_name == "spot.tickers":
            symbol = data.get("currency_pair")
            token_volume = data.get("base_volume")
            usdt_volume = data.get("quote_volume")
            logger.info(
                "GATE.IO | %s | TOKEN_VOLUME: %s | USDT_VOLUME: %s",
                symbol, token_volume, usdt_volume,
            )

    async def view_messages(self) -> None:
        while True:
            message = await recv_with_timeout(self.websocket, DEFAULT_READ_TIMEOUT)
            self.handle_message(message)


async def run_gateio() -> None:
    socket = GateioSocket()
    await run_socket_forever(
        "GATE.IO",
        connect=socket.connect,
        subscribe=socket.subscribe,
        consume=socket.view_messages,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_gateio())

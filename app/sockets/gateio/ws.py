"""Gate.io spot WebSocket client (book_ticker + ticker channels)."""
import asyncio
import json
import time
from typing import List, Optional

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosedError

from app.sockets.gateio.symbols import gateio_symbols

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
        """Fetch the list of tradable pairs from the Gate.io REST API."""
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

    async def view_messages(self) -> None:
        try:
            async for message in self.websocket:
                stream = json.loads(message)
                stream_name = stream.get("channel")
                data = stream.get("result")

                if data is None or stream.get("event") != "update":
                    continue

                if "book_ticker" in stream_name:
                    symbol = data.get("s")
                    ask, ask_q = data.get("a"), data.get("A")
                    bid, bid_q = data.get("b"), data.get("B")
                    print(f"GATE.IO | {symbol} | ASK: {ask} | ASKQ: {ask_q} | BID: {bid} | BIDQ: {bid_q}")
                elif stream_name == "spot.tickers":
                    symbol = data.get("currency_pair")
                    token_volume = data.get("base_volume")
                    usdt_volume = data.get("quote_volume")
                    print(f"GATE.IO | {symbol} | TOKEN_VOLUME: {token_volume} | USDT_VOLUME: {usdt_volume}")
        except ConnectionClosedError:
            # Reconnect and re-subscribe on an unexpected close.
            await self.connect()
            await self.sub_book(pairs=self.symbols)
            await self.view_messages()


gateio = GateioSocket()


async def run_gateio() -> None:
    await gateio.connect()
    await gateio.sub_book(pairs=gateio.symbols)
    await gateio.view_messages()


if __name__ == "__main__":
    asyncio.run(run_gateio())

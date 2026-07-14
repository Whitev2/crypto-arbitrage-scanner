"""OKX spot WebSocket client (order-book top-5 + ticker)."""
import asyncio
import json

import websockets

from app.sockets.okx.symbols import okx_symbols

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

    async def view_messages(self) -> None:
        async for message in self.websocket:
            stream = json.loads(message)
            stream_name = stream.get("arg", {}).get("channel", "")
            data = stream.get("data", [None])[0]
            if data is None:
                continue

            symbol = data.get("instId")

            if "books" in stream_name:
                ask, ask_q = data["asks"][0][0], data["asks"][0][1]
                bid, bid_q = data["bids"][0][0], data["bids"][0][1]
                print(f"OKX | {symbol} | ASK: {ask} | ASKQ: {ask_q} | BID: {bid} | BIDQ: {bid_q}")
            elif "tickers" in stream_name:
                token_volume = data.get("vol24h")
                usdt_volume = data.get("volCcy24h")
                print(f"OKX | {symbol} | TOKEN_VOLUME: {token_volume} | USDT_VOLUME: {usdt_volume}")


okx = OKXSocket()


async def run_okx() -> None:
    await okx.connect()

    for symbol in okx.symbols:
        await okx.sub_book(symbol)
        await okx.sub_ticker(symbol)

    await okx.view_messages()


if __name__ == "__main__":
    asyncio.run(run_okx())

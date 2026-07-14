"""Huobi (HTX) spot WebSocket client (ticker channel, gzip framed)."""
import asyncio
import gzip
import json

import websockets

from app.sockets.huobi.symbols import huobi_symbols

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

    async def view_messages(self) -> None:
        async for message in self.websocket:
            if isinstance(message, bytes):
                message = gzip.decompress(message)

            stream = json.loads(message)

            # Huobi requires a pong reply to keep the connection alive.
            if stream.get("ping"):
                await self.websocket.send(json.dumps({"pong": stream["ping"]}))
                continue

            stream_name = stream.get("ch", "")
            data = stream.get("tick")

            if "ticker" in stream_name and data:
                ask = data.get("ask")
                ask_q = data.get("askSize")

                bid = data.get("bid")
                bid_q = data.get("bidSize")

                symbol = stream_name.split(".")[1].upper()
                usdt_volume = data.get("vol")
                print(
                    f"HUOBI | {symbol} | ASK: {ask} | ASKQ: {ask_q} | "
                    f"BID: {bid} | BIDQ: {bid_q} | USDT_VOLUME: {usdt_volume}"
                )


huobi = HuobiSocket()


async def run_huobi() -> None:
    await huobi.connect()

    for symbol in huobi.symbols:
        await huobi.sub_ticker(symbol)

    await huobi.view_messages()


if __name__ == "__main__":
    asyncio.run(run_huobi())

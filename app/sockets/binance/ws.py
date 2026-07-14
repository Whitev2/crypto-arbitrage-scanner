"""Binance spot WebSocket client (best bid/ask + rolling ticker)."""
import asyncio
import json

import websockets

from app.sockets.binance.symbols import binance_symbols

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

    async def view_messages(self) -> None:
        async for message in self.websocket:
            stream = json.loads(message)

            stream_name = stream.get("stream", "")
            data = stream.get("data", {})
            symbol = data.get("s")

            if "bookTicker" in stream_name:
                ask = data.get("a")
                ask_q = data.get("A")

                bid = data.get("b")
                bid_q = data.get("B")

                print(f"BINANCE | {symbol} | ASK: {ask} | ASKQ: {ask_q} | BID: {bid} | BIDQ: {bid_q}")
            elif "ticker" in stream_name:
                token_volume = data.get("v")
                usdt_volume = data.get("q")
                print(f"BINANCE | {symbol} | TOKEN_VOLUME: {token_volume} | USDT_VOLUME: {usdt_volume}")


binance = BinanceSocket()


async def run_binance() -> None:
    await binance.connect()
    await binance.view_messages()


if __name__ == "__main__":
    asyncio.run(run_binance())

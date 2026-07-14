import itertools
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Quote:
    exchange: str
    symbol: str
    ask: Decimal
    bid: Decimal


@dataclass(frozen=True)
class Opportunity:
    symbol: str
    buy_exchange: str
    buy_price: Decimal
    sell_exchange: str
    sell_price: Decimal
    spread_pct: Decimal


def _to_decimal(value) -> Optional[Decimal]:
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return dec if dec > 0 else None


class SpreadCalculator:
    def __init__(self, threshold_pct: float = 0.5):
        self.threshold_pct = Decimal(str(threshold_pct))

    @staticmethod
    def spread_pct(buy_price: Decimal, sell_price: Decimal) -> Decimal:
        return (sell_price - buy_price) / buy_price * Decimal(100)

    def best_opportunity(self, symbol: str, quotes: List[Quote]) -> Optional[Opportunity]:
        # перебираем пары бирж, берём самый широкий положительный спред
        best: Optional[Opportunity] = None

        for buy, sell in itertools.permutations(quotes, 2):
            if buy.ask is None or sell.bid is None:
                continue

            spread = self.spread_pct(buy.ask, sell.bid)
            if spread <= 0:
                continue

            if best is None or spread > best.spread_pct:
                best = Opportunity(
                    symbol=symbol,
                    buy_exchange=buy.exchange,
                    buy_price=buy.ask,
                    sell_exchange=sell.exchange,
                    sell_price=sell.bid,
                    spread_pct=spread,
                )

        if best is not None and best.spread_pct >= self.threshold_pct:
            return best
        return None

    def scan(self, quotes_by_symbol: Dict[str, List[Quote]]) -> List[Opportunity]:
        opportunities = []
        for symbol, quotes in quotes_by_symbol.items():
            opportunity = self.best_opportunity(symbol, quotes)
            if opportunity is not None:
                opportunities.append(opportunity)
        return opportunities


def build_quote(exchange: str, symbol: str, ask, bid) -> Optional[Quote]:
    # битые значения отбрасываем
    ask_dec = _to_decimal(ask)
    bid_dec = _to_decimal(bid)
    if ask_dec is None or bid_dec is None:
        return None
    return Quote(exchange=exchange, symbol=symbol, ask=ask_dec, bid=bid_dec)

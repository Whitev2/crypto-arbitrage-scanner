"""Cross-exchange spread calculation.

Given the latest best bid/ask quotes for a symbol across several exchanges,
find the most profitable buy-low / sell-high pair and, when the spread clears
the configured threshold, surface it as an arbitrage opportunity.
"""
import itertools
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Quote:
    """Best bid/ask for a single (exchange, symbol) pair."""

    exchange: str
    symbol: str
    ask: Decimal  # lowest price we can buy at
    bid: Decimal  # highest price we can sell at


@dataclass(frozen=True)
class Opportunity:
    """A profitable buy-on-A / sell-on-B combination for one symbol."""

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
        # Minimum spread (in %) worth reporting as an opportunity.
        self.threshold_pct = Decimal(str(threshold_pct))

    @staticmethod
    def spread_pct(buy_price: Decimal, sell_price: Decimal) -> Decimal:
        """Percentage gain of selling at ``sell_price`` after buying at ``buy_price``."""
        return (sell_price - buy_price) / buy_price * Decimal(100)

    def best_opportunity(self, symbol: str, quotes: List[Quote]) -> Optional[Opportunity]:
        """Return the single most profitable exchange pair for ``symbol``, if any.

        For every ordered pair of exchanges we consider buying at one venue's
        ask and selling at the other's bid, then keep the widest positive spread.
        """
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
        """Scan every symbol and collect opportunities above the threshold."""
        opportunities = []
        for symbol, quotes in quotes_by_symbol.items():
            opportunity = self.best_opportunity(symbol, quotes)
            if opportunity is not None:
                opportunities.append(opportunity)
        return opportunities


def build_quote(exchange: str, symbol: str, ask, bid) -> Optional[Quote]:
    """Build a :class:`Quote` from raw values, dropping malformed entries."""
    ask_dec = _to_decimal(ask)
    bid_dec = _to_decimal(bid)
    if ask_dec is None or bid_dec is None:
        return None
    return Quote(exchange=exchange, symbol=symbol, ask=ask_dec, bid=bid_dec)

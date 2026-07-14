"""Unit tests for the pure spread-calculation logic.

These cover the raw percentage maths, the currency/decimal parsing in
``build_quote`` / ``_to_decimal``, the best-opportunity selection and the
threshold gating in :class:`SpreadCalculator`.
"""
from decimal import Decimal

import pytest

from app.spread.spread_calculator import (
    Opportunity,
    Quote,
    SpreadCalculator,
    _to_decimal,
    build_quote,
)


# --------------------------------------------------------------------------- #
# _to_decimal / build_quote (currency + decimal handling)
# --------------------------------------------------------------------------- #
class TestToDecimal:
    def test_parses_string_price(self):
        assert _to_decimal("123.45") == Decimal("123.45")

    def test_parses_float_price_exactly(self):
        # Going via str() avoids binary float noise: 0.1 stays 0.1.
        assert _to_decimal(0.1) == Decimal("0.1")

    def test_parses_int_price(self):
        assert _to_decimal(42) == Decimal("42")

    def test_rejects_zero(self):
        assert _to_decimal(0) is None

    def test_rejects_negative(self):
        assert _to_decimal("-5") is None

    def test_rejects_none(self):
        assert _to_decimal(None) is None

    def test_rejects_garbage_string(self):
        assert _to_decimal("not-a-number") is None


class TestBuildQuote:
    def test_builds_valid_quote(self):
        quote = build_quote("binance", "BTC-USDT", ask="100.5", bid="100.0")
        assert quote == Quote(
            exchange="binance",
            symbol="BTC-USDT",
            ask=Decimal("100.5"),
            bid=Decimal("100.0"),
        )

    def test_drops_quote_with_bad_ask(self):
        assert build_quote("okx", "BTC-USDT", ask="oops", bid="100") is None

    def test_drops_quote_with_bad_bid(self):
        assert build_quote("okx", "BTC-USDT", ask="100", bid=None) is None

    def test_drops_quote_with_zero_price(self):
        assert build_quote("okx", "BTC-USDT", ask="0", bid="100") is None


# --------------------------------------------------------------------------- #
# spread_pct (pure maths)
# --------------------------------------------------------------------------- #
class TestSpreadPct:
    def test_positive_spread(self):
        # buy at 100, sell at 110 -> +10%
        assert SpreadCalculator.spread_pct(Decimal("100"), Decimal("110")) == Decimal("10")

    def test_zero_spread(self):
        assert SpreadCalculator.spread_pct(Decimal("100"), Decimal("100")) == Decimal("0")

    def test_negative_spread(self):
        assert SpreadCalculator.spread_pct(Decimal("100"), Decimal("90")) == Decimal("-10")

    def test_fractional_spread_is_exact(self):
        # Decimal maths must be exact, not float-approximate.
        assert SpreadCalculator.spread_pct(Decimal("200"), Decimal("201")) == Decimal("0.5")


# --------------------------------------------------------------------------- #
# best_opportunity (selection + threshold)
# --------------------------------------------------------------------------- #
class TestBestOpportunity:
    def test_finds_profitable_pair(self):
        calc = SpreadCalculator(threshold_pct=0.5)
        quotes = [
            Quote("binance", "BTC-USDT", ask=Decimal("100"), bid=Decimal("99")),
            Quote("okx", "BTC-USDT", ask=Decimal("105"), bid=Decimal("104")),
        ]
        opp = calc.best_opportunity("BTC-USDT", quotes)
        assert opp is not None
        # Buy cheapest ask (binance 100), sell highest bid (okx 104).
        assert opp.buy_exchange == "binance"
        assert opp.buy_price == Decimal("100")
        assert opp.sell_exchange == "okx"
        assert opp.sell_price == Decimal("104")
        assert opp.spread_pct == Decimal("4")

    def test_returns_none_when_below_threshold(self):
        calc = SpreadCalculator(threshold_pct=5.0)
        quotes = [
            Quote("binance", "BTC-USDT", ask=Decimal("100"), bid=Decimal("99")),
            Quote("okx", "BTC-USDT", ask=Decimal("101"), bid=Decimal("101")),
        ]
        # Best spread is only 1%, threshold is 5% -> no opportunity.
        assert calc.best_opportunity("BTC-USDT", quotes) is None

    def test_spread_exactly_at_threshold_is_reported(self):
        calc = SpreadCalculator(threshold_pct=1.0)
        quotes = [
            Quote("a", "BTC-USDT", ask=Decimal("100"), bid=Decimal("100")),
            Quote("b", "BTC-USDT", ask=Decimal("101"), bid=Decimal("101")),
        ]
        opp = calc.best_opportunity("BTC-USDT", quotes)
        assert opp is not None
        assert opp.spread_pct == Decimal("1")

    def test_returns_none_when_no_profitable_pair(self):
        calc = SpreadCalculator(threshold_pct=0.5)
        # All asks >= all bids across venues -> never profitable.
        quotes = [
            Quote("a", "BTC-USDT", ask=Decimal("100"), bid=Decimal("99")),
            Quote("b", "BTC-USDT", ask=Decimal("100"), bid=Decimal("99")),
        ]
        assert calc.best_opportunity("BTC-USDT", quotes) is None

    def test_returns_none_for_single_quote(self):
        calc = SpreadCalculator(threshold_pct=0.5)
        quotes = [Quote("a", "BTC-USDT", ask=Decimal("100"), bid=Decimal("99"))]
        assert calc.best_opportunity("BTC-USDT", quotes) is None

    def test_returns_none_for_empty_quotes(self):
        calc = SpreadCalculator(threshold_pct=0.5)
        assert calc.best_opportunity("BTC-USDT", []) is None

    def test_picks_widest_of_several(self):
        calc = SpreadCalculator(threshold_pct=0.5)
        quotes = [
            Quote("a", "BTC-USDT", ask=Decimal("100"), bid=Decimal("100")),
            Quote("b", "BTC-USDT", ask=Decimal("102"), bid=Decimal("103")),
            Quote("c", "BTC-USDT", ask=Decimal("110"), bid=Decimal("112")),
        ]
        opp = calc.best_opportunity("BTC-USDT", quotes)
        assert opp is not None
        # Widest: buy a@100, sell c@112 -> 12%.
        assert opp.buy_exchange == "a"
        assert opp.sell_exchange == "c"
        assert opp.spread_pct == Decimal("12")


# --------------------------------------------------------------------------- #
# scan (multi-symbol aggregation)
# --------------------------------------------------------------------------- #
class TestScan:
    def test_scan_collects_only_above_threshold(self):
        calc = SpreadCalculator(threshold_pct=2.0)
        quotes_by_symbol = {
            "BTC-USDT": [
                Quote("a", "BTC-USDT", ask=Decimal("100"), bid=Decimal("100")),
                Quote("b", "BTC-USDT", ask=Decimal("101"), bid=Decimal("105")),  # 5%
            ],
            "ETH-USDT": [
                Quote("a", "ETH-USDT", ask=Decimal("100"), bid=Decimal("100")),
                Quote("b", "ETH-USDT", ask=Decimal("100.5"), bid=Decimal("101")),  # 1%
            ],
        }
        opps = calc.scan(quotes_by_symbol)
        assert len(opps) == 1
        assert opps[0].symbol == "BTC-USDT"
        assert all(isinstance(o, Opportunity) for o in opps)

    def test_scan_empty_input(self):
        calc = SpreadCalculator(threshold_pct=0.5)
        assert calc.scan({}) == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

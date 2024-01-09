"""
Test ticker
"""

from kcbot.ticker import Ticker


def test_ticker() -> None:
    ticker_response = {
        "bestAsk": 1.1234,
        "bestBid": 1.5678,
    }
    daystats_response = {
        "high": 1.9876,
        "low": 1.0123,
    }
    tick = Ticker.from_kucoin(ticker_response, daystats_response)
    assert tick.header() == "      Ask,       Bid,      High,       Low"
    assert tick.info() == "    1.123,     1.568,     1.988,     1.012"

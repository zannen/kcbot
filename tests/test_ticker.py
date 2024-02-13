"""
Test ticker
"""

from kcbot.ticker import Ticker


def test_ticker() -> None:
    ticker_response = {
        "bestAsk": 1.12345,
        "bestBid": 1.56789,
    }
    daystats_response = {
        "high": 1.98765,
        "low": 1.01234,
    }
    tick = Ticker.from_kucoin(ticker_response, daystats_response)
    assert tick.header() == "      Ask,       Bid,      High,       Low"
    assert tick.info() == "   1.1235,    1.5679,    1.9876,    1.0123"

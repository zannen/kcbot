"""
A class for a Ticker object.
"""

from typing import Any, Dict


class Ticker:
    """
    A Ticker object.
    """

    ask = 0.0
    bid = 0.0
    high = 0.0
    low = 0.0

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @classmethod
    def from_kucoin(
        cls,
        tick: Dict[str, Any],
        day_stats: Dict[str, Any],
    ) -> "Ticker":
        """
        Create a Ticker object from a KuCoin API response.
        """
        return Ticker(
            ask=float(tick["bestAsk"]),
            bid=float(tick["bestBid"]),
            high=float(day_stats["high"]),
            low=float(day_stats["low"]),
        )

    def header(self) -> str:
        """
        Return a nicely formatted header line.
        """
        ask, bid, hig, low = "Ask", "Bid", "High", "Low"
        return f"{ask:>9s}, {bid:>9s}, {hig:>9s}, {low:>9s}"

    def info(self) -> str:
        """
        Return a nicely formatted information line.
        """
        return (
            f"{self.ask:9.4f}, {self.bid:9.4f}, "
            f"{self.high:9.4f}, {self.low:9.4f}"
        )

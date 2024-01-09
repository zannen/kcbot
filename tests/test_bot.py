"""
Test bot
"""

import uuid
from typing import Any, Dict, List

import kcbot.bot


def mock_uuid4():
    return uuid.UUID("0" * 32)


ASK = 105.01
BID = 104.99
LOW = 100.0
HIGH = 110.0


class MockMarket:
    def get_24h_stats(self, market: str) -> Dict[str, Any]:
        return {
            "symbol": "XYZ-ZZZ",
            "high": str(HIGH),
            "low": str(LOW),
        }

    def get_ticker(self, market: str) -> Dict[str, Any]:
        return {
            "bestAsk": str(ASK),
            "bestBid": str(BID),
        }


class MockTrade:
    pass


AVAIL_BASE = 100.0  # for sell orders
AVAIL_QUOTE = 200.0  # for buy orders


class MockUser:
    def get_account_list(self, account_type: str = "") -> List[Dict[str, Any]]:
        return [
            {
                "available": AVAIL_BASE,
                "currency": "XYZ",
            },
            {
                "available": AVAIL_QUOTE,
                "currency": "ZZZ",
            },
        ]


def test_bot(monkeypatch) -> None:
    monkeypatch.setattr(kcbot.bot.uuid, "uuid4", mock_uuid4)
    monkeypatch.setattr(kcbot.bot.kcc, "Market", MockMarket)
    monkeypatch.setattr(kcbot.bot.kcc, "Trade", MockTrade)
    monkeypatch.setattr(kcbot.bot.kcc, "User", MockUser)
    BUY_VOL_PERCENT = 50.0
    SELL_VOL_PERCENT = 50.0
    cfg = {
        "base": "XYZ",
        "buy": {
            "pcnt_bump_a": 1.0,
            "pcnt_bump_c": 1.0,
            "order_count": 2,
            "vol_percent": BUY_VOL_PERCENT,
        },
        "loglevel": "INFO",
        "quote": "ZZZ",
        "sell": {
            "pcnt_bump_a": 1.0,
            "pcnt_bump_c": 1.0,
            "order_count": 2,
            "vol_percent": SELL_VOL_PERCENT,
        },
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})

    bot.load_config()
    assert bot.base == "XYZ"

    bot.get_balances()
    assert bot.balances == {
        "XYZ": 100.0,
        "ZZZ": 200.0,
    }

    bot.get_ticker()

    buys = bot.buy_orders()
    assert all(float(order["price"]) < LOW for order in buys)
    assert (
        sum(float(order["price"]) * float(order["size"]) for order in buys)
        < AVAIL_QUOTE * BUY_VOL_PERCENT
    )

    sells = bot.sell_orders()
    assert all(float(order["price"]) > HIGH for order in sells)
    assert (
        sum(float(order["price"]) * float(order["size"]) for order in buys)
        < AVAIL_BASE * SELL_VOL_PERCENT
    )

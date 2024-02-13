"""
Test bot
"""

from typing import Any, Dict

import kcbot.bot

from .conftest import create_mock_market, create_mock_trade, create_mock_user


def test_bot_config(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 104.0, 106.0, 110.0),
    )
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    assert bot.base == base
    assert bot.quote == quote
    assert bot.tick_len == 60


def test_bot_balances(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    avail_base = 100.0
    avail_quote = 200.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, avail_base, avail_quote),
    )
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()

    bot.get_balances()
    assert bot.balances == {
        base: avail_base,
        quote: avail_quote,
    }


def test_bot_buy_daylow(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    low = 100.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, low, 104.0, 106.0, 110.0),
    )
    avail_quote = 200.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, 100.0, avail_quote),
    )
    buy_vol_percent = 50.0
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "day-high-low",
                "buy": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": buy_vol_percent,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    buys = bot.buy_orders(cfg["strategies"][0])
    assert all(float(order["price"]) < low for order in buys)
    assert (
        sum(float(order["price"]) * float(order["size"]) for order in buys)
        < avail_quote * buy_vol_percent
    )


def test_bot_sell_dayhigh(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    high = 110.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 104.0, 106.0, high),
    )
    avail_base = 100.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, avail_base, 200.0),
    )
    sell_vol_percent = 50.0
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "day-high-low",
                "sell": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": sell_vol_percent,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    sells = bot.sell_orders(cfg["strategies"][0])
    assert all(float(order["price"]) > high for order in sells)
    assert (
        sum(float(order["size"]) for order in sells)
        < avail_base * sell_vol_percent
    )


def test_bot_buy_bestbid(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    bid = 104.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, bid, 106.0, 110.0),
    )
    avail_quote = 200.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, 100.0, avail_quote),
    )
    buy_vol_percent = 50.0
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "bid-and-ask",
                "buy": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": buy_vol_percent,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    buys = bot.buy_orders(cfg["strategies"][0])
    assert all(float(order["price"]) < bid for order in buys)
    assert (
        sum(float(order["price"]) * float(order["size"]) for order in buys)
        < avail_quote * buy_vol_percent
    )


def test_bot_sell_bestask(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    ask = 106.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 104.0, ask, 110.0),
    )
    avail_base = 100.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, avail_base, 200.0),
    )
    sell_vol_percent = 50.0
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "bid-and-ask",
                "sell": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": sell_vol_percent,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    sells = bot.sell_orders(cfg["strategies"][0])
    assert all(float(order["price"]) > ask for order in sells)
    assert (
        sum(float(order["size"]) for order in sells)
        < avail_base * sell_vol_percent
    )


def test_bot_buy_avg(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 108.0, 109.0, 110.0),
    )
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, 100.0, 200.0),
    )
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "bid-and-ask",
                "buy": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": 50.0,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    buys = bot.buy_orders(cfg["strategies"][0])
    assert len(buys) == 2


def test_bot_sell_avg(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 101.0, 102.0, 110.0),
    )
    avail_base = 100.0
    avail_quote = 200.0
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, avail_base, avail_quote),
    )
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "bid-and-ask",
                "sell": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": 50.0,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    sells = bot.sell_orders(cfg["strategies"][0])
    assert len(sells) == 2


def test_bot_nobuy_avg(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 101.0, 102.0, 110.0),
    )
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, 100.0, 200.0),
    )
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "bid-or-ask",
                "buy": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": 50.0,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    buys = bot.buy_orders(cfg["strategies"][0])
    assert len(buys) == 0


def test_bot_nosell_avg(monkeypatch) -> None:
    base = "SOMETOKEN"
    quote = "GBPT"
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Market",
        create_mock_market(base, quote, 100.0, 108.0, 109.0, 110.0),
    )
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "User",
        create_mock_user(base, quote, 100.0, 200.0),
    )
    cfg: Dict[str, Any] = {
        "base": base,
        "loglevel": "INFO",
        "quote": quote,
        "strategies": [
            {
                "name": "careful",
                "strategy": "bid-or-ask",
                "sell": {
                    "pcnt_bump_a": 1.0,
                    "pcnt_bump_c": 1.0,
                    "order_count": 2,
                    "vol_percent": 50.0,
                },
            },
        ],
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    bot.get_balances()
    bot.get_ticker()

    sells = bot.sell_orders(cfg["strategies"][0])
    assert len(sells) == 0


def test_bot_resell(monkeypatch) -> None:
    mock_orders = {
        "buy-done": [
            {
                "currentPage": 1,
                "items": [
                    {
                        "createdAt": 1706256825125,
                        "dealSize": "10",
                        "price": "1.0000",
                        "side": "buy",
                        "size": "123.456",
                    },
                ],
                "pageSize": 500,
                "totalNum": 1,
                "totalPage": 1,
            }
        ],
        "sell-active": [
            {
                "currentPage": 1,
                "items": [],
                "pageSize": 500,
                "totalNum": 0,
                "totalPage": 1,
            }
        ],
        "sell-done": [
            {
                "currentPage": 1,
                "items": [],
                "pageSize": 500,
                "totalNum": 0,
                "totalPage": 1,
            }
        ],
    }
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Trade",
        create_mock_trade(mock_orders),
    )
    cfg: Dict[str, Any] = {
        "loglevel": "DEBUG",
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    orders = bot.opposite_orders(False, "resell")
    assert len(orders) == 1
    order = orders[0]
    assert order["side"] == "sell"
    assert order["price"] == "1.05"


def test_bot_resell_already_active(monkeypatch) -> None:
    mock_orders = {
        "buy-done": [
            {
                "currentPage": 1,
                "items": [
                    {
                        "createdAt": 1700000000000,
                        "dealSize": "10",
                        "price": "1.0000",
                        "side": "buy",
                    },
                ],
                "pageSize": 500,
                "totalNum": 1,
                "totalPage": 1,
            }
        ],
        "sell-active": [
            {
                "currentPage": 1,
                "items": [
                    {
                        "createdAt": 1700000000000,
                        "size": "10",
                        "price": "1.0500",
                        "side": "sell",
                    },
                ],
                "pageSize": 500,
                "totalNum": 1,
                "totalPage": 1,
            }
        ],
        "sell-done": [
            {
                "currentPage": 1,
                "items": [],
                "pageSize": 500,
                "totalNum": 0,
                "totalPage": 1,
            }
        ],
    }
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Trade",
        create_mock_trade(mock_orders),
    )
    cfg: Dict[str, Any] = {
        "loglevel": "DEBUG",
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    orders = bot.opposite_orders(False, "resell")
    assert len(orders) == 0


def test_bot_resell_already_done(monkeypatch) -> None:
    mock_orders = {
        "buy-done": [
            {
                "currentPage": 1,
                "items": [
                    {
                        "createdAt": 1700000000000,
                        "dealSize": "10",
                        "price": "1.0000",
                        "side": "buy",
                    },
                ],
                "pageSize": 500,
                "totalNum": 1,
                "totalPage": 1,
            }
        ],
        "sell-active": [
            {
                "currentPage": 1,
                "items": [],
                "pageSize": 500,
                "totalNum": 0,
                "totalPage": 1,
            }
        ],
        "sell-done": [
            {
                "currentPage": 1,
                "items": [
                    {
                        "createdAt": 1700000000000,
                        "dealSize": "10",
                        "price": "1.0500",
                        "side": "sell",
                    },
                ],
                "pageSize": 500,
                "totalNum": 1,
                "totalPage": 1,
            }
        ],
    }
    monkeypatch.setattr(
        kcbot.bot.kcc,
        "Trade",
        create_mock_trade(mock_orders),
    )
    cfg: Dict[str, Any] = {
        "loglevel": "DEBUG",
        "tick_len": 60,
    }
    bot = kcbot.bot.Bot(config=cfg, keys={})
    bot.load_config()
    orders = bot.opposite_orders(False, "resell")
    assert len(orders) == 0

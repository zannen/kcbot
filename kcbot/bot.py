"""
KCBot: A simple KuCoin trading bot.
"""

import json
import logging
import math
import time
import uuid
from typing import Any, Dict, List, Union

import kucoin.client as kcc

from .ticker import Ticker


class Bot:
    def __init__(
        self,
        config: Union[str, Dict[str, Any]] = "",
        keys: Union[str, Dict[str, Any]] = "",
    ):
        self.balances: Dict[str, float] = {}
        self.base = "?"
        self.buy = {
            "pcnt_bump_a": 0.1,
            "pcnt_bump_c": 0.1,
            "order_count": 0,
            "vol_percent": 0.0,
        }
        self.loglevel = "INFO"
        self.mkt = "?-?"
        self.quote = "?"
        self.sell = {
            "pcnt_bump_a": 0.1,
            "pcnt_bump_c": 0.1,
            "order_count": 0,
            "vol_percent": 0.0,
        }
        self.tick_len = 86400
        self.ticker = Ticker()

        self.config = config
        if isinstance(keys, str):
            with open(keys, "r", encoding="utf-8") as keysf:
                thekeys = json.load(keysf)
        else:
            thekeys = keys
        self.init_api(thekeys)

        logging.basicConfig(
            level=logging.INFO,
            format=(
                "%(asctime)s %(name)s:%(levelname)-5s "
                "[%(funcName)s:%(lineno)4d] %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger("KCBot")

    def init_api(self, keys: Dict[str, Any]) -> None:
        self.market = kcc.Market(**keys)
        self.trade = kcc.Trade(**keys)
        self.user = kcc.User(**keys)

    def get_balances(self):
        accounts = self.user.get_account_list(account_type="trade")
        # self.logger.debug(
        #     "accounts: %s",
        #     json.dumps(accounts, indent=2, sort_keys=True),
        # )
        bal_base = float(
            [acc for acc in accounts if acc["currency"] == self.base][0][
                "available"
            ]
        )
        bal_quot = float(
            [acc for acc in accounts if acc["currency"] == self.quote][0][
                "available"
            ]
        )
        self.balances = {
            self.base: bal_base,
            self.quote: bal_quot,
        }
        self.logger.info(
            "Balances: %f %s, %f %s",
            bal_base,
            self.base,
            bal_quot,
            self.quote,
        )

    def get_ticker(self):
        self.ticker = Ticker.from_kucoin(
            self.market.get_ticker(self.mkt),
            self.market.get_24h_stats(self.mkt),
        )
        self.logger.info(
            "Ticker for %s (in %s): %s",
            self.mkt,
            self.quote,
            self.ticker.header(),
        )
        self.logger.info(
            "Ticker for %s (in %s): %s",
            self.mkt,
            self.quote,
            self.ticker.info(),
        )

    def load_config(self):
        if isinstance(self.config, str):
            with open(self.config, encoding="utf-8") as configf:
                cfg = json.load(configf)
        else:
            cfg = self.config

        for cfg_key, cfg_val in cfg.items():
            setattr(self, cfg_key, cfg_val)
            # self.logger.debug("config: %s = %s", cfg_key, str(cfg_val))

        self.logger.setLevel(self.loglevel)
        self.mkt = f"{self.base}-{self.quote}"

    def loop(self):
        while True:
            self.load_config()
            self.get_balances()
            self.get_ticker()
            self.tick("BUY", self.buy_orders())
            self.tick("SELL", self.sell_orders())
            self.logger.info("Sleeping for %d seconds", self.tick_len)
            try:
                time.sleep(self.tick_len)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break

    def buy_orders(self) -> List[Dict[str, Any]]:
        self.logger.info("--- Buy %s ---", self.mkt)
        buy_order_count = int(self.buy["order_count"])
        if buy_order_count == 0:
            return []
        bal_quote = self.balances[self.quote]
        bal_base = bal_quote / self.ticker.bid
        self.logger.info(
            "Balance: %10.3f %s (approx %10.3f %s)",
            bal_quote,
            self.quote,
            bal_base,
            self.base,
        )
        vol_total = sum(math.sqrt(i) for i in range(1, buy_order_count + 1))
        vol_p = self.buy["vol_percent"]
        vol_mul = bal_base / vol_total * vol_p / 100.0
        base_price = self.ticker.low
        orders: List[Dict[str, Any]] = []
        for n in range(1, buy_order_count + 1):
            pcnt_bump_buy = (
                self.buy["pcnt_bump_a"] * n**2 + self.buy["pcnt_bump_c"]
            )
            p_buy = round(base_price * (1 - pcnt_bump_buy / 100), 4)
            if p_buy <= 0.0:
                self.logger.warning(
                    "Skipping buy order. price=%9.4f %s",
                    p_buy,
                    self.quote,
                )
                continue

            vol_buy = round(vol_mul * math.sqrt(n), 4)
            order = {
                "clientOid": str(uuid.uuid4()),
                "side": "buy",
                "symbol": self.mkt,
                "type": "limit",
                "stp": "DC",
                "price": str(p_buy),
                "size": str(vol_buy),
                "timeInForce": "GTT",
                "cancelAfter": self.tick_len,
            }
            orders.append(order)
            self.logger.info(
                "Order: BUY  %9.4f %5s for %7.2f %4s (%8.3f %s/%s)",
                vol_buy,
                self.base,
                vol_buy * p_buy,
                self.quote,
                p_buy,
                self.quote,
                self.base,
            )

        return orders

    def sell_orders(self) -> List[Dict[str, Any]]:
        sell_order_count = int(self.sell["order_count"])
        if sell_order_count == 0:
            return []

        self.logger.info("--- Sell %s ---", self.mkt)

        bal_base = self.balances[self.base]
        if bal_base < 100:
            self.logger.info("Not enough tokens (%f)", bal_base)
            return []

        self.logger.info("Balance: %10.3f %s", bal_base, self.base)
        vol_total = sum(math.sqrt(i) for i in range(1, sell_order_count + 1))
        vol_p = self.sell["vol_percent"]
        vol_mul = bal_base / vol_total * vol_p / 100.0
        base_price = self.ticker.high
        orders: List[Dict[str, Any]] = []
        for n in range(1, sell_order_count + 1):
            pcnt_bump_sell = (
                self.sell["pcnt_bump_a"] * n**2 + self.sell["pcnt_bump_c"]
            )
            p_sell = round(base_price * (1 + pcnt_bump_sell / 100), 4)

            vol_sell = round(vol_mul * math.sqrt(n), 4)

            order = {
                "clientOid": str(uuid.uuid4()),
                "side": "sell",
                "symbol": self.mkt,
                "type": "limit",
                "stp": "DC",
                "price": str(p_sell),
                "size": str(vol_sell),
                "timeInForce": "GTT",
                "cancelAfter": self.tick_len,
            }
            orders.append(order)
            self.logger.info(
                "Order: SELL %9.4f %5s for %7.2f %4s (%8.3f %s/%s)",
                vol_sell,
                self.base,
                vol_sell * p_sell,
                self.quote,
                p_sell,
                self.quote,
                self.base,
            )

        return orders

    def tick(self, side: str, orders: List[Dict[str, Any]]) -> int:
        count = 0
        for i in range(0, len(orders), 5):
            batch = orders[slice(i, i + 5)]
            # self.logger.debug(
            #     "%s batch: %s",
            #     side,
            #     json.dumps(batch, indent=2, sort_keys=True),
            # )
            result = self.trade.create_bulk_orders(self.mkt, batch)
            # self.logger.debug(
            #     "Bulk %s order results: %s",
            #     side,
            #     json.dumps(result, indent=2, sort_keys=True),
            # )
            failed = [
                res for res in result["data"] if res["failMsg"] is not None
            ]
            count += len(batch) - len(failed)

        self.logger.info("Placed %d/%d %s orders", count, len(orders), side)
        return count
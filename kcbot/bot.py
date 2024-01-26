"""
KCBot: A simple KuCoin trading bot.
"""

import datetime
import json
import logging
import math
import os
import time
import traceback
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
        self.strategies: List[Dict[str, Any]] = []
        self.loglevel = "INFO"
        self.mkt = "?-?"
        self.quote = "?"
        self.tick_len = 86400
        self.ticker = Ticker()

        self.config = config
        if isinstance(keys, str):
            with open(keys, "r", encoding="utf-8") as keysf:
                thekeys = json.load(keysf)
        else:
            thekeys = keys

        self.market = kcc.Market(**thekeys)
        self.trade = kcc.Trade(**thekeys)
        self.user = kcc.User(**thekeys)

        logging.basicConfig(
            level=logging.INFO,
            format=(
                "%(asctime)s %(name)s:%(levelname)-5s "
                "[%(funcName)s:%(lineno)4d] %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger("KCBot")

    def get_all(self, func, cached: bool, **kwargs) -> List[Dict[str, Any]]:
        pages: List[Dict[str, Any]] = []
        filename = kwargs["side"] + "_" + kwargs["status"] + ".json"
        if cached:
            self.logger.debug(
                "Getting %s %s orders (cached)",
                kwargs["status"],
                kwargs["side"],
            )
            with open(filename, encoding="utf-8") as handle:
                pages = json.load(handle)
            return pages

        self.logger.debug(
            "Getting %s %s orders, page 1",
            kwargs["status"],
            kwargs["side"],
        )
        kwargs["currentPage"] = 1
        kwargs["pageSize"] = 500
        pages.append(func(**kwargs))
        page_count = pages[0]["totalPage"]
        if page_count > 1:
            for page in range(2, page_count + 1):
                kwargs["currentPage"] = page
                self.logger.debug(
                    "Getting %s %s orders, page %d/%d",
                    kwargs["status"],
                    kwargs["side"],
                    page,
                    page_count,
                )
                pages.append(func(**kwargs))

        with open(filename, "w", encoding="utf-8") as handle:
            json.dump(pages, handle, sort_keys=True, indent=2)

        self.logger.debug(
            "Got %s %s orders, total %d",
            kwargs["status"],
            kwargs["side"],
            pages[0]["totalNum"],
        )
        return pages

    def opposite_orders(
        self,
        cached: bool,
        direction: str,
    ) -> List[Dict[str, Any]]:
        """
        Create opposite direction orders.
        :param direction:
          - "resell" to add new sell orders opposite to executed buy orders
          - "rebuy" to add new buy orders opposite to executed sell orders.
        """
        open_dir = "buy" if direction == "resell" else "sell"
        close_dir = "sell" if direction == "resell" else "buy"
        start = datetime.datetime.utcnow()
        start -= datetime.timedelta(seconds=self.tick_len * 2)
        start_at = int(start.timestamp() * 1000.0)

        openorder_pages = self.get_all(
            self.trade.get_order_list,
            cached,
            status="done",
            symbol=self.mkt,
            side=open_dir,
            tradeType="TRADE",  # spot
            type="limit",
            startAt=start_at,
        )
        closeorder_active_pages = self.get_all(
            self.trade.get_order_list,
            cached,
            status="active",
            symbol=self.mkt,
            side=close_dir,
            tradeType="TRADE",  # spot
            type="limit",
            startAt=start_at,
        )
        closeorder_done_pages = self.get_all(
            self.trade.get_order_list,
            cached,
            status="done",
            symbol=self.mkt,
            side=close_dir,
            tradeType="TRADE",  # spot
            type="limit",
            startAt=start_at,
        )

        openorders: List[Dict[str, Any]] = []
        for openorder_page in openorder_pages:
            for openorder in openorder_page["items"]:
                if openorder["dealSize"] != "0":
                    openorders.append(openorder)
        openorders = sorted(
            openorders, key=lambda item: item["createdAt"], reverse=True
        )

        closeorders_active: List[Dict[str, Any]] = []
        for closeorder_active_page in closeorder_active_pages:
            closeorders_active.extend(closeorder_active_page["items"])
        closeorders_active = sorted(
            closeorders_active,
            key=lambda item: item["createdAt"],
            reverse=True,
        )

        closeorders_done: List[Dict[str, Any]] = []
        for closeorder_done_page in closeorder_done_pages:
            closeorders_done.extend(closeorder_done_page["items"])
        closeorders_done = sorted(
            closeorders_done, key=lambda item: item["createdAt"], reverse=True
        )

        new_orders: List[Dict[str, Any]] = []
        for openorder in openorders:
            price = float(openorder["price"])
            size = float(openorder["dealSize"])
            if close_dir == "sell":
                # open-low-buy => close-high-sell
                expected_close_price_min = price * 1.045
                expected_close_price_max = price * 1.055
            else:
                # open-high-sell => close-low-buy
                expected_close_price_min = price * 0.945
                expected_close_price_max = price * 0.955
            matching_closeorders_active = [
                closeorder
                for closeorder in closeorders_active
                if abs(float(closeorder["size"]) - size) < 0.0001
                and float(closeorder["price"]) > expected_close_price_min
                and float(closeorder["price"]) < expected_close_price_max
            ]
            matching_closeorders_done = [
                closeorder
                for closeorder in closeorders_done
                if abs(float(closeorder["dealSize"]) - size) < 0.0001
                and float(closeorder["price"]) > expected_close_price_min
                and float(closeorder["price"]) < expected_close_price_max
            ]
            openorder_created_at = datetime.datetime.fromtimestamp(
                int(openorder["createdAt"] / 1000.0)
            )
            self.logger.debug(
                "%s %s %10.4f at %9.4f",
                openorder_created_at.isoformat(),
                open_dir,
                size,
                price,
            )
            if matching_closeorders_active:
                for mch in matching_closeorders_active:
                    closeorder_created_at = datetime.datetime.fromtimestamp(
                        int(mch["createdAt"] / 1000.0)
                    )
                    self.logger.debug(
                        "--> %s %s %10.4f at %9.4f",
                        closeorder_created_at.isoformat(),
                        close_dir,
                        float(mch["size"]),
                        float(mch["price"]),
                    )

            if matching_closeorders_done:
                for mch in matching_closeorders_done:
                    closeorder_created_at = datetime.datetime.fromtimestamp(
                        int(mch["createdAt"] / 1000.0)
                    )
                    self.logger.debug(
                        "--> (%s %s %10.4f at %9.4f, done)",
                        closeorder_created_at.isoformat(),
                        close_dir,
                        float(mch["dealSize"]),
                        float(mch["price"]),
                    )

            if (
                not matching_closeorders_active
                and not matching_closeorders_done
            ):
                if close_dir == "sell":
                    # open-low-buy => close-high-sell
                    close_price = round(price * 1.05, 4)
                else:
                    # open-high-sell => close-low-buy
                    close_price = round(price * 0.95, 4)
                self.logger.debug(
                    "--> SHOULD %s %10.4f at %9.4f",
                    close_dir,
                    size,
                    close_price,
                )
                new_order = {
                    "clientOid": str(uuid.uuid4()),
                    "side": close_dir,
                    "symbol": self.mkt,
                    "type": "limit",
                    "stp": "DC",
                    "price": str(close_price),
                    "size": str(size),
                    "timeInForce": "GTC",
                }
                new_orders.append(new_order)

        return new_orders

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
            try:
                self.load_config()
                self.get_balances()
                self.get_ticker()
                self.create_orders(
                    "REBUY",
                    self.opposite_orders(False, "rebuy"),
                )
                self.create_orders(
                    "RESELL",
                    self.opposite_orders(False, "resell"),
                )
                for strategy in self.strategies:
                    self.tick(strategy)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break
            except Exception:
                self.logger.warning(
                    "Caught exception while looping.%s%s",
                    os.linesep,
                    traceback.format_exc(),
                )

            try:
                self.logger.info("Sleeping for %d seconds", self.tick_len)
                time.sleep(self.tick_len)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break

    def tick(self, strategy: Dict[str, Any]) -> None:
        self.create_orders("BUY", self.buy_orders(strategy))
        self.create_orders("SELL", self.sell_orders(strategy))

    def buy_orders(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.logger.info("--- Buy %s ---", self.mkt)
        buy_order_count = int(strategy["buy"]["order_count"])
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
        vol_p = strategy["buy"]["vol_percent"]
        vol_mul = bal_base / vol_total * vol_p / 100.0
        if strategy["strategy"] == "day-high-low":
            base_price = self.ticker.low
        elif strategy["strategy"] == "bid-and-ask":
            base_price = self.ticker.bid
        elif strategy["strategy"] == "bid-or-ask":
            avg = (self.ticker.high + self.ticker.low) / 2.0
            if self.ticker.bid < avg:
                self.logger.info(
                    "Buy: bid < avg (%8.4f < %8.4f)",
                    self.ticker.bid,
                    avg,
                )
                return []
            base_price = self.ticker.bid
        else:
            raise Exception("Unknown strategy: " + strategy["strategy"])
        orders: List[Dict[str, Any]] = []
        for n in range(1, buy_order_count + 1):
            pcnt_bump_buy = (
                strategy["buy"]["pcnt_bump_a"] * n**2
                + strategy["buy"]["pcnt_bump_c"]
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
                "Order: BUY  %9.4f %5s for %7.2f %4s (%8.4f %s/%s)",
                vol_buy,
                self.base,
                vol_buy * p_buy,
                self.quote,
                p_buy,
                self.quote,
                self.base,
            )

        return orders

    def sell_orders(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        sell_order_count = int(strategy["sell"]["order_count"])
        if sell_order_count == 0:
            return []

        self.logger.info("--- Sell %s ---", self.mkt)

        bal_base = self.balances[self.base]
        if bal_base < 100:
            self.logger.info("Not enough tokens (%f)", bal_base)
            return []

        self.logger.info("Balance: %10.3f %s", bal_base, self.base)
        vol_total = sum(math.sqrt(i) for i in range(1, sell_order_count + 1))
        vol_p = strategy["sell"]["vol_percent"]
        vol_mul = bal_base / vol_total * vol_p / 100.0
        if strategy["strategy"] == "day-high-low":
            base_price = self.ticker.high
        elif strategy["strategy"] == "bid-and-ask":
            base_price = self.ticker.ask
        elif strategy["strategy"] == "bid-or-ask":
            avg = (self.ticker.high + self.ticker.low) / 2.0
            if self.ticker.ask > avg:
                self.logger.info(
                    "Sell: ask > avg (%8.4f > %8.4f)",
                    self.ticker.ask,
                    avg,
                )
                return []
            base_price = self.ticker.ask
        else:
            raise Exception("Unknown strategy: " + strategy["strategy"])
        orders: List[Dict[str, Any]] = []
        for n in range(1, sell_order_count + 1):
            pcnt_bump_sell = (
                strategy["sell"]["pcnt_bump_a"] * n**2
                + strategy["sell"]["pcnt_bump_c"]
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
                "Order: SELL %9.4f %5s for %7.2f %4s (%8.4f %s/%s)",
                vol_sell,
                self.base,
                vol_sell * p_sell,
                self.quote,
                p_sell,
                self.quote,
                self.base,
            )

        return orders

    def create_orders(self, side: str, orders: List[Dict[str, Any]]) -> int:
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

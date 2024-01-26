from typing import Any, Dict, List


def create_mock_market(
    base: str,
    quote: str,
    low: float,
    bid: float,
    ask: float,
    high: float,
):
    class MockMarket:
        def get_24h_stats(self, market: str) -> Dict[str, Any]:
            return {
                "symbol": f"{base}-{quote}",
                "high": str(high),
                "low": str(low),
            }

        def get_ticker(self, market: str) -> Dict[str, Any]:
            return {
                "bestAsk": str(ask),
                "bestBid": str(bid),
            }

    return MockMarket


def create_mock_trade(order_lists: Dict[str, List[Dict[str, Any]]]):
    class MockTrade:
        def get_order_list(self, **kwargs) -> Dict[str, Any]:
            order_list = order_lists[kwargs["side"] + "-" + kwargs["status"]]
            return order_list[kwargs["currentPage"] - 1]

    return MockTrade


def create_mock_user(
    base: str,
    quote: str,
    avail_base: float,
    avail_quote: float,
):
    class MockUser:
        def get_account_list(
            self,
            account_type: str = "",
        ) -> List[Dict[str, Any]]:
            return [
                {
                    "available": avail_base,
                    "currency": base,
                },
                {
                    "available": avail_quote,
                    "currency": quote,
                },
            ]

    return MockUser

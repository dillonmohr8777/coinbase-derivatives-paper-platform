import httpx

from app.data import CoinbasePublicProvider


def test_coinbase_perpetual_discovery_and_candle_normalization():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [
                        {
                            "product_id": "BTC-PERP-INTX",
                            "display_name": "BTC PERP",
                            "price": "60000",
                            "best_bid_price": "59999",
                            "best_ask_price": "60001",
                            "base_increment": "0.0001",
                            "quote_increment": "0.01",
                            "base_min_size": "0.001",
                            "product_type": "FUTURE",
                            "trading_disabled": False,
                            "future_product_details": {
                                "index_price": "60000.5",
                                "perpetual_details": {
                                    "open_interest": "1200",
                                    "funding_rate": "0.0001",
                                    "max_leverage": "10",
                                },
                            },
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "candles": [
                    {
                        "start": "1735689900",
                        "low": "99",
                        "high": "102",
                        "open": "100",
                        "close": "101",
                        "volume": "10",
                    },
                    {
                        "start": "1735689600",
                        "low": "98",
                        "high": "101",
                        "open": "99",
                        "close": "100",
                        "volume": "8",
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = CoinbasePublicProvider(client)
    product = provider.list_perpetuals()[0]
    assert product.product_id == "BTC-PERP-INTX"
    assert product.funding_rate == 0.0001 and product.max_leverage == 10
    candles = provider.get_candles("BTC-PERP-INTX", "5m", 2)
    assert len(candles) == 2 and candles[0].ts < candles[1].ts
    assert candles[-1].close == 101


def test_coinbase_provider_rejects_unknown_timeframe():
    provider = CoinbasePublicProvider(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    )
    try:
        provider.get_candles("BTC-PERP-INTX", "2m")
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unknown timeframe should fail closed")

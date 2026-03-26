import io
import pytest

from converters.trading212 import convert_trading212

SAMPLE_CSV = """\
Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),ID,Currency conversion fee,Withholding tax,Currency (Withholding tax)
Market buy,2025-01-10 10:00:00,US0378331005,AAPL,Apple,10,150.00,USD,1.0,1500.00,USD,TX001,,
Market sell,2025-01-20 11:00:00,US0378331005,AAPL,Apple,10,160.00,USD,1.0,1600.00,USD,TX002,,
Dividend (Ordinary),2025-01-15 09:00:00,US5949181045,MSFT,Microsoft,,,USD,1.0,25.00,USD,TX003,,5.00,USD
"""


@pytest.fixture
def result():
    return convert_trading212(io.StringIO(SAMPLE_CSV))


def test_counts(result):
    trades, income = result
    assert len(trades) == 2
    assert len(income) == 1


def test_buy_trade(result):
    trades, _ = result
    buy = next(t for t in trades if t["direction"] == "BUY")
    assert buy["tx_id"] == "TX001"
    assert buy["symbol"] == "AAPL"


def test_sell_trade(result):
    trades, _ = result
    sell = next(t for t in trades if t["direction"] == "SELL")
    assert sell["tx_id"] == "TX002"
    assert sell["direction"] == "SELL"


def test_dividend(result):
    _, income = result
    div = income[0]
    assert div["tx_id"] == "TX003"
    assert div["wht_amount"] == "5.00"
    assert div["income_type"] == "DIVIDEND"

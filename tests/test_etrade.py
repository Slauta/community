import io
import pytest

from converters.etrade import convert_etrade

SAMPLE_CSV = """\
TransactionDate,Type,Description,Symbol,Quantity,Price,Commission,Amount,NetProceeds
04/14/23,Bought,APPLE INC COM,AAPL,10,150.00,0.00,-1500.00,-1500.00
04/15/23,Dividend,MICROSOFT CORP,MSFT,,0.75,,7.50,7.50
04/20/23,Sold,TESLA INC,TSLA,5,200.00,0.01,1000.00,999.99
"""


@pytest.fixture
def result():
    return convert_etrade(io.StringIO(SAMPLE_CSV))


def test_counts(result):
    trades, income = result
    assert len(trades) == 2
    assert len(income) == 1


def test_buy_trade(result):
    trades, _ = result
    buy = next(t for t in trades if t["direction"] == "BUY")
    assert buy["symbol"] == "AAPL"
    assert buy["amount"] == "1500.00"
    assert buy["currency"] == "USD"


def test_sell_trade(result):
    trades, _ = result
    sell = next(t for t in trades if t["direction"] == "SELL")
    assert sell["symbol"] == "TSLA"
    assert sell["commission"] == "0.01"


def test_dividend(result):
    _, income = result
    div = income[0]
    assert div["tx_id"] == "MSFT:DIV:2023-04-15"
    assert div["gross_amount"] == "7.50"
    assert div["income_type"] == "DIVIDEND"

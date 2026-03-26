import io
import pytest

from converters.schwab import convert_schwab

SAMPLE_CSV = """\
"Date","Action","Symbol","Description","Quantity","Price","Fees & Comm","Amount"
"12/08/2025","Buy","AAPL","APPLE INC","10","$150.00","","$-1500.00"
"12/09/2025","Sell","AAPL","APPLE INC","10","$160.00","$0.10","$1599.90"
"12/10/2025","Qualified Dividend","MSFT","MICROSOFT CORP","","","","$25.00"
"12/10/2025","NRA Tax Adj","MSFT","MICROSOFT CORP","","","","-$5.00"
"12/11/2025","Credit Interest","","SCHWAB1 INT","","","","$0.50"
"""


@pytest.fixture
def result():
    return convert_schwab(io.StringIO(SAMPLE_CSV))


def test_counts(result):
    trades, income = result
    assert len(trades) == 2
    assert len(income) == 2


def test_buy_trade(result):
    trades, _ = result
    buy = next(t for t in trades if t["direction"] == "BUY")
    assert buy["symbol"] == "AAPL"
    assert buy["direction"] == "BUY"
    assert buy["country"] == "US"
    assert buy["currency"] == "USD"
    assert buy["broker"] == "SCHWAB"


def test_sell_trade_commission_and_gross(result):
    trades, _ = result
    sell = next(t for t in trades if t["direction"] == "SELL")
    assert sell["commission"] == "0.10"
    # gross = net proceeds + commission = 1599.90 + 0.10 = 1600.00
    assert sell["amount"] == "1600.00"


def test_dividend_with_wht(result):
    _, income = result
    div = next(r for r in income if r["income_type"] == "DIVIDEND")
    assert div["symbol"] == "MSFT"
    assert div["gross_amount"] == "25.00"
    assert div["wht_amount"] == "5.00"


def test_interest(result):
    _, income = result
    interest = next(r for r in income if r["income_type"] == "INTEREST")
    assert interest["symbol"] == "USD-INT"
    assert interest["income_type"] == "INTEREST"


def test_tx_ids_non_empty(result):
    trades, income = result
    for row in trades + income:
        assert row["tx_id"], f"Empty tx_id in row: {row}"

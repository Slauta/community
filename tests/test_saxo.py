from pathlib import Path
import pytest

DATA_FILE = Path(__file__).parent.parent / "data" / "saxo_tax_report.xlsx"

pytestmark = pytest.mark.skipif(
    not DATA_FILE.exists(),
    reason="saxo_tax_report.xlsx not found in data/"
)


@pytest.fixture(scope="module")
def result():
    from converters.saxo import convert_saxo
    return convert_saxo(str(DATA_FILE))


def test_returns_at_least_one_trade_and_income(result):
    trades, income = result
    assert len(trades) >= 1
    assert len(income) >= 1


def test_trade_broker_and_direction(result):
    trades, _ = result
    for trade in trades:
        assert trade["broker"] == "SAXO"
        assert trade["direction"] in ("BUY", "SELL")


def test_orsted_sell_trade(result):
    trades, _ = result
    orsted = next((t for t in trades if t["symbol"] == "ORSTED_T"), None)
    assert orsted is not None, "Expected ORSTED_T trade"
    assert orsted["direction"] == "SELL"
    assert orsted["country"] == "DK"


def test_income_dividend_currency(result):
    _, income = result
    for rec in income:
        assert rec["income_type"] == "DIVIDEND"
        assert rec["currency"] in ("USD", "EUR", "DKK")

from pathlib import Path
import pytest

DATA_FILE = Path(__file__).parent.parent / "data" / "freedom_report_2025.xlsx"

pytestmark = pytest.mark.skipif(
    not DATA_FILE.exists(),
    reason="freedom_report_2025.xlsx not found in data/"
)


@pytest.fixture(scope="module")
def result():
    from converters.freedom_ru import convert_freedom_ru
    return convert_freedom_ru(str(DATA_FILE))


def test_returns_lists(result):
    trades, income = result
    assert isinstance(trades, list)
    assert isinstance(income, list)


def test_trade_fields(result):
    trades, _ = result
    assert trades, "Expected at least one trade"
    for trade in trades:
        assert trade["broker"] == "Freedom"
        assert trade["direction"] in ("BUY", "SELL"), f"Unexpected direction: {trade['direction']}"
        assert trade["symbol"], "symbol should be non-empty"
        assert trade["currency"], "currency should be non-empty"


def test_income_fields(result):
    _, income = result
    assert income, "Expected at least one income record"
    for rec in income:
        assert rec["income_type"] in ("DIVIDEND", "INTEREST", "EQUITY_SWAP"), (
            f"Unexpected income_type: {rec['income_type']}"
        )
        assert rec["gross_amount"], "gross_amount should be non-empty"

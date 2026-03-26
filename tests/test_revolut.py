from pathlib import Path
import pytest

DATA_FILE = Path(__file__).parent.parent / "data" / "72605457-D9F9-44C3-8F07-0146B7508287.pdf"

pytestmark = pytest.mark.skipif(
    not DATA_FILE.exists(),
    reason="Revolut PDF not found in data/"
)


@pytest.fixture(scope="module")
def result():
    from converters.revolut import convert_revolut
    return convert_revolut(str(DATA_FILE))


def test_returns_empty_trades(result):
    trades, _ = result
    assert trades == []


def test_income_count(result):
    _, income = result
    assert len(income) == 2


def test_income_fields(result):
    _, income = result
    for rec in income:
        assert rec["broker"] == "Revolut"
        assert rec["income_type"] == "DIVIDEND"
        assert rec["currency"] == "EUR"
        assert rec["wht_amount"] == "0"


def test_tx_id_format(result):
    _, income = result
    import re
    pattern = re.compile(r'^[A-Z0-9]+:DIV:\d{4}-\d{2}-\d{2}$')
    for rec in income:
        assert pattern.match(rec["tx_id"]), f"Unexpected tx_id format: {rec['tx_id']}"

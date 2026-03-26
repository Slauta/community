import io
import pytest

from converters.bunq import convert_bunq

SAMPLE_CSV = """\
Date,Description,Amount,Balance
2025-01-25,bunq Payday 2025-01-25 EUR,12.50,1012.50
2025-01-26,iDEAL payment,-50.00,962.50
2025-02-25,bunq Payday 2025-02-25 EUR,13.00,975.50
"""


@pytest.fixture
def result():
    return convert_bunq(io.StringIO(SAMPLE_CSV))


def test_returns_empty_trades(result):
    trades, _ = result
    assert trades == []


def test_income_count(result):
    _, income = result
    # Only "bunq Payday" rows are included; iDEAL payment is skipped
    assert len(income) == 2


def test_income_type_and_currency(result):
    _, income = result
    for rec in income:
        assert rec["income_type"] == "INTEREST"
        assert rec["currency"] == "EUR"


def test_tx_id_format(result):
    _, income = result
    assert income[0]["tx_id"] == "EUR-INT:2025-01-25"
    assert income[1]["tx_id"] == "EUR-INT:2025-02-25"

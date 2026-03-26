import csv
import io
from pathlib import Path

import pytest

from converters import REGISTRY, detect_converter, _detect_schwab, _detect_etrade, _detect_freedom_ru, _detect_saxo, _detect_revolut

REQUIRED_KEYS = {"id", "broker", "report_type", "detect", "convert", "input_type"}


def test_registry_entries_have_required_keys():
    for entry in REGISTRY:
        missing = REQUIRED_KEYS - set(entry.keys())
        assert not missing, f"Entry '{entry.get('id')}' missing keys: {missing}"


def test_registry_ids_are_unique():
    ids = [entry["id"] for entry in REGISTRY]
    assert len(ids) == len(set(ids)), "Duplicate IDs in REGISTRY"


def test_detect_converter_unrecognized_file(tmp_path):
    f = tmp_path / "random_file.txt"
    f.write_text("this is not a broker report\nsome random text\n")
    result = detect_converter(f)
    assert result is None


def test_detect_schwab_true(tmp_path):
    f = tmp_path / "schwab.csv"
    f.write_text('"Date","Action","Symbol","Description","Quantity","Price","Fees & Comm","Amount"\n')
    assert _detect_schwab(f) is True


def test_detect_schwab_false_no_fees_col(tmp_path):
    f = tmp_path / "other.csv"
    f.write_text("Date,Action,Symbol,Description\n")
    assert _detect_schwab(f) is False


def test_detect_etrade_true(tmp_path):
    f = tmp_path / "etrade.csv"
    f.write_text("TransactionDate,Type,Description,Symbol,Quantity,Price,Commission,Amount,NetProceeds\n")
    assert _detect_etrade(f) is True


def test_detect_etrade_false(tmp_path):
    f = tmp_path / "other.csv"
    f.write_text("Date,Type,Description\n")
    assert _detect_etrade(f) is False


def test_detect_freedom_ru_real(data_dir):
    xlsx = data_dir / "freedom_report_2025.xlsx"
    if not xlsx.exists():
        pytest.skip("freedom_report_2025.xlsx not found in data/")
    assert _detect_freedom_ru(xlsx) is True


def test_detect_saxo_real(data_dir):
    xlsx = data_dir / "saxo_tax_report.xlsx"
    if not xlsx.exists():
        pytest.skip("saxo_tax_report.xlsx not found in data/")
    assert _detect_saxo(xlsx) is True


def test_detect_revolut_real(data_dir):
    pdf = data_dir / "72605457-D9F9-44C3-8F07-0146B7508287.pdf"
    if not pdf.exists():
        pytest.skip("Revolut PDF not found in data/")
    assert _detect_revolut(pdf) is True

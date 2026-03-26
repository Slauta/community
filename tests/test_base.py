import io
from pathlib import Path

from converters.base import write_csv, out_path


def test_write_csv_header_and_rows():
    rows = [
        {"broker": "TEST", "symbol": "AAPL", "amount": "100.00"},
        {"broker": "TEST", "symbol": "MSFT", "amount": "200.00"},
    ]
    buf = io.StringIO()
    write_csv(buf, rows)
    content = buf.getvalue()

    lines = content.splitlines()
    assert lines[0] == "broker,symbol,amount"
    assert "TEST" in lines[1]
    assert "AAPL" in lines[1]
    assert len(lines) == 3


def test_write_csv_single_row():
    rows = [{"a": "1", "b": "2"}]
    buf = io.StringIO()
    write_csv(buf, rows)
    lines = buf.getvalue().splitlines()
    assert lines[0] == "a,b"
    assert lines[1] == "1,2"


def test_out_path_explicit():
    result = out_path("/custom/path/out.csv", "/some/dir", "default.csv")
    assert result == "/custom/path/out.csv"


def test_out_path_output_dir():
    result = out_path(None, "/some/dir", "trades.csv")
    assert result == str(Path("/some/dir") / "trades.csv")


def test_out_path_filename_only():
    result = out_path(None, None, "trades.csv")
    assert result == "trades.csv"


def test_out_path_explicit_wins_over_dir():
    result = out_path("/explicit.csv", "/output", "default.csv")
    assert result == "/explicit.csv"

# community — Broker Report Converter

Converts broker transaction reports (CSV, XLSX, PDF) into a unified CSV format
suitable for tax reporting and portfolio analysis.

![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-unknown-lightgrey)

---

## Supported Brokers

| Broker | Format | Report Type | Auto-detected by |
|---|---|---|---|
| Schwab | CSV | Transaction Report | `"Fees & Comm"` column in header |
| E\*TRADE | CSV | Transaction Report | `TransactionDate` + `NetProceeds` columns |
| Trading 212 | CSV | Trade Export | `ISIN` + `Ticker` + `Action` columns |
| bunq | CSV | Bank Statement | `bunq` in file content |
| Freedom Finance (RU) | XLSX | Russian Report | Sheet name starts with `ExecTrades` |
| Freedom Finance (EN) | XLSX | English Report | `Instrument/trade type` in first row |
| Saxo | XLSX | Tax Report | Sheets `PNL` and `WithHoldings` |
| eToro | XLSX | Account Statement | Sheet `Closed Positions` |
| Revolut | PDF | P&L Statement | `Revolut Securities` text on first page |

---

## Output Schema

### Trades CSV

| Field | Description |
|---|---|
| `broker` | Broker identifier (e.g. `SCHWAB`, `ETRADE`, `T212`) |
| `tx_id` | Unique transaction ID (broker-native or derived) |
| `direction` | `BUY` or `SELL` |
| `symbol` | Ticker symbol (e.g. `AAPL`) |
| `isin` | ISIN code, or empty string |
| `country` | ISO 2-letter country code derived from ISIN or broker data |
| `currency` | ISO 3-letter currency code (e.g. `USD`) |
| `price` | Price per share as a decimal string |
| `quantity` | Number of shares as a decimal string |
| `amount` | Gross trade amount (before commission) as a decimal string |
| `commission` | Commission/fees paid as a decimal string |
| `operation_datetime` | ISO 8601 date or datetime of the trade |
| `settlement_date` | ISO 8601 settlement date |

### Income CSV

| Field | Description |
|---|---|
| `broker` | Broker identifier |
| `tx_id` | Unique transaction ID |
| `income_type` | `DIVIDEND`, `INTEREST`, or `EQUITY_SWAP` |
| `symbol` | Ticker symbol or synthetic symbol (e.g. `USD-INT`) |
| `currency` | ISO 3-letter currency code |
| `gross_amount` | Gross income amount before withholding tax |
| `wht_amount` | Withholding tax amount (0 if none) |
| `operation_datetime` | ISO 8601 date or datetime of the income event |
| `settlement_date` | ISO 8601 settlement date |

---

## Quick Start (local)

**Prerequisites:** Python 3.12+, optionally [uv](https://docs.astral.sh/uv/)

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run:**
```bash
python run.py
# or with uv (handles Python version and deps automatically):
uv run run.py
```

**Options:**
```
--input-dir DIR    Directory with broker report files (default: data/)
--output-dir DIR   Directory for output CSV files (default: output/)
```

Example:
```bash
python run.py --input-dir ~/Downloads/broker-reports --output-dir ~/tax-2025
```

---

## Quick Start (Docker)

```bash
docker build -t broker-converter .
docker run -it \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  broker-converter
```

Place your broker report files in `data/` before running. Results will appear
in `output/` on your host machine.

---

## How run.py Works

1. **Scan** — `run.py` scans all files in `--input-dir` (default: `data/`).
2. **Detect** — Each file is tested against every converter's `detect`
   function. The first match wins.
3. **Confirm / override** — An interactive table lists detected files and their
   assigned converters. Press **Enter** to proceed, or enter space-separated
   file numbers to change the converter for specific files (you can also choose
   to skip a file).
4. **Convert** — Each file is passed to its converter. CSV-input converters
   receive an open `TextIO`; XLSX/PDF converters receive the file path string.
5. **Output** — Trades and income are written to separate CSV files in
   `--output-dir`. File names follow the pattern
   `result_trades_<stem>_<suffix>.csv` / `result_income_<stem>_<suffix>.csv`.
   The output directory is cleared at the start of each run.

---

## Adding a New Converter

Use `converters/etrade.py` as a reference — it is the simplest converter.

### Step 1 — Create `converters/<broker>.py`

```python
# converters/mybroker.py
import csv
from decimal import Decimal

BROKER = 'MYBROKER'

def convert_mybroker(infile):
    """Convert MyBroker CSV. Returns (trade_rows, income_rows)."""
    trade_rows = []
    income_rows = []
    for row in csv.DictReader(infile):
        # parse and append to trade_rows or income_rows
        pass
    return trade_rows, income_rows
```

### Step 2 — Add `_detect_<broker>` in `converters/__init__.py`

```python
def _detect_mybroker(path):
    if path.suffix.lower() != '.csv':
        return False
    h = _csv_header(path)
    return 'MyBroker' in h and 'UniqueColumn' in h
```

### Step 3 — Add an entry to `REGISTRY`

```python
{
    'id': 'mybroker',
    'broker': 'MyBroker',
    'report_type': 'Transaction Report',
    'detect': _detect_mybroker,
    'convert': convert_mybroker,
    'input_type': 'csv',   # or 'xlsx' / 'pdf'
},
```

And add the import at the top of `converters/__init__.py`:
```python
from .mybroker import convert_mybroker
```

### Step 4 — Write tests in `tests/test_mybroker.py`

Use `io.StringIO` for CSV converters; reference a real file (with
`pytest.skip`) for XLSX/PDF converters. See the existing test files for
examples.

---

## Development Setup

```bash
git clone <repo-url>
cd community
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests for one converter
pytest tests/test_schwab.py -v

# Short traceback for failures
pytest tests/ --tb=short
```

---

## Code Conventions

- **Each converter module** contains only conversion logic — no `argparse`,
  no file I/O beyond reading the input.
- **Return type** is always `(trade_rows, income_rows)` — a tuple of two
  lists of dicts.
- **Monetary values** are stored as strings of `Decimal` (no floats, no
  rounding surprises).
- **`tx_id` strategy:**
  - Use the broker-native transaction ID when available.
  - Otherwise use `SYMBOL:TYPE:DATE` (e.g. `MSFT:DIV:2025-01-15`).
  - As a last resort, compute a SHA-1 hash over a stable set of fields and
    take the first 16 hex characters.
- **Date format:** ISO 8601 — `YYYY-MM-DD` for dates,
  `YYYY-MM-DDTHH:MM:SS` for datetimes.
- **`input_type`:**
  - `'csv'` — the converter receives an open `TextIO` object.
  - `'xlsx'` or `'pdf'` — the converter receives the file path as a `str`.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Add a converter module and detection function following the steps above.
3. Write tests in `tests/test_<broker>.py` — at minimum cover: record counts,
   key field values, and `tx_id` format.
4. Ensure `pytest` passes before opening a pull request.
5. Keep converter modules self-contained; avoid adding new dependencies
   without updating `requirements.txt`.

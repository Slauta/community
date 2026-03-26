# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Python toolkit for converting financial transaction exports from various brokers/banks into a standardized CSV format for tax reporting and financial analysis.

## Running

```bash
# With uv (manages Python version and deps automatically):
uv run run.py

# Or directly:
pip install -r requirements.txt
python run.py

# Options:
python run.py --input-dir ~/Downloads/broker-reports --output-dir ~/tax-2025
```

`run.py` scans `--input-dir` (default: `data/`), auto-detects each file's broker, shows an interactive confirmation table, then converts and writes CSVs to `--output-dir` (default: `output/`). The output directory is cleared at the start of each run.

## Development

```bash
pip install -r requirements-dev.txt
pytest                        # all tests
pytest tests/test_schwab.py -v
pytest tests/ --tb=short
```

## Architecture

`converters/` is the core package:

- `converters/__init__.py` — `REGISTRY` list + `detect_converter(path)`. Each entry has `id`, `broker`, `report_type`, `detect` (callable), `convert` (callable), `input_type` (`'csv'` / `'xlsx'` / `'pdf'`).
- `converters/base.py` — shared `write_csv` and `out_path` utilities.
- One module per broker (`schwab.py`, `saxo.py`, `freedom.py`, `freedom_ru.py`, `trading212.py`, `bunq.py`, `etrade.py`, `etoro.py`, `revolut.py`).

**`input_type` contract:**
- `'csv'` — converter receives an open `TextIO` object.
- `'xlsx'` or `'pdf'` — converter receives the file path as a `str`.

Every converter returns `(trade_rows, income_rows)` — a tuple of two lists of dicts.

### Output Schema

**Trades CSV** (`result_trades_<stem>_<suffix>.csv`):
```
broker, tx_id, direction, symbol, isin, country, currency,
price, quantity, amount, commission, operation_datetime, settlement_date
```

**Income CSV** (`result_income_<stem>_<suffix>.csv`):
```
broker, tx_id, income_type, symbol, currency, gross_amount,
wht_amount, operation_datetime, settlement_date
```

### Code Conventions

- Monetary values are `str(Decimal(...))` — no floats.
- Dates: `YYYY-MM-DD`; datetimes: `YYYY-MM-DDTHH:MM:SS`.
- `tx_id` strategy: broker-native ID → `SYMBOL:TYPE:DATE` → SHA1 hex[:16].
- Country codes: ISO 2-letter, extracted from ISIN prefix when possible.

## Adding a New Converter

Use `converters/etrade.py` as the simplest reference.

1. Create `converters/<broker>.py` — implement `convert_<broker>(infile_or_path)` returning `(trade_rows, income_rows)`.
2. Add `_detect_<broker>(path)` in `converters/__init__.py`.
3. Add an entry to `REGISTRY` in `converters/__init__.py` and import the converter at the top.
4. Write tests in `tests/test_<broker>.py`.

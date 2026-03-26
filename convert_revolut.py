#!/usr/bin/env python3

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pdfplumber",
# ]
# ///

import argparse
import csv
import hashlib
import os
import re
from decimal import Decimal
from pathlib import Path

import pdfplumber


BROKER = 'Revolut'

_CURRENCY_SYMBOLS = {'€': 'EUR', '$': 'USD', '£': 'GBP'}
_ISIN_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{10})\b')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_AMOUNT_RE = re.compile(r'(?:US)?([€$£])([\d,]+\.?\d*)')


def convert_revolut(pdf_path: str) -> tuple[list[dict], list[dict]]:
    """Convert Revolut Securities PDF P&L statement.

    Returns (trade_rows, income_rows).
    """
    trade_rows = []
    income_rows = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            lines = text.splitlines()

            if _is_sells_detail(lines):
                trade_rows.extend(_parse_sells(lines))
            elif _is_income_detail(lines):
                income_rows.extend(_parse_income(lines))

    return trade_rows, income_rows


# ---------------------------------------------------------------------------
# Page type detection
# ---------------------------------------------------------------------------

def _is_sells_detail(lines: list[str]) -> bool:
    """Sells detail page has 'Date acquired' and 'Date sold' column headers."""
    return any('Date acquired' in l and 'Date sold' in l for l in lines)


def _is_income_detail(lines: list[str]) -> bool:
    """Income detail page has 'Date', 'Description', and 'ISIN' column headers."""
    return any('Date' in l and 'Description' in l and 'ISIN' in l for l in lines)


# ---------------------------------------------------------------------------
# Income parser
# ---------------------------------------------------------------------------

def _parse_income(lines: list[str]) -> list[dict]:
    """Parse 'Other income & fees' data lines."""
    rows = []
    in_table = False

    for line in lines:
        if 'Date' in line and 'Description' in line and 'ISIN' in line:
            in_table = True
            continue

        if not in_table:
            continue

        if line.strip().startswith('Rate:') or 'PLN' in line:
            continue

        if line.strip().startswith('Total'):
            in_table = False
            continue

        row = _parse_income_line(line)
        if row:
            rows.append(row)

    return rows


def _parse_income_line(line: str) -> dict | None:
    """Parse one income data line.

    Format: {date} {symbol} {security name + type} {isin} {country} {gross} {wht} {net}
    Example: 2025-11-28 IQQH iShares Global Clean Energy Dist ETF dividend IE00B1XNHC34 IE €1.51 - €1.51
    """
    isin_m = _ISIN_RE.search(line)
    if not isin_m:
        return None

    before = line[:isin_m.start()].strip()
    after = line[isin_m.end():].strip()
    isin = isin_m.group(1)

    parts = before.split()
    if len(parts) < 2 or not _DATE_RE.match(parts[0]):
        return None

    date = parts[0]
    symbol = parts[1]
    description = ' '.join(parts[2:]).lower()

    after_parts = after.split()
    country = after_parts[0] if after_parts else ''

    amounts = _AMOUNT_RE.findall(after)
    if not amounts:
        return None

    currency_char, gross_str = amounts[0]
    currency = _CURRENCY_SYMBOLS.get(currency_char, 'USD')
    gross = Decimal(gross_str.replace(',', ''))

    # WHT column: '-' means no withholding tax.
    first_amount_end = after.index(gross_str) + len(gross_str)
    between = after[first_amount_end:]
    wht = Decimal('0')
    amt_m = _AMOUNT_RE.search(between)
    if amt_m and not re.search(r'(?<!\d)-(?!\d)', between[:amt_m.start()]):
        if len(amounts) >= 3:
            wht = Decimal(amounts[1][1].replace(',', ''))

    income_type = 'INTEREST' if 'interest' in description else 'DIVIDEND'
    type_tag = 'INT' if income_type == 'INTEREST' else 'DIV'
    tx_id = f'{symbol}:{type_tag}:{date}'

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'income_type': income_type,
        'symbol': symbol,
        'isin': isin,
        'country': country,
        'currency': currency,
        'gross_amount': str(gross),
        'wht_amount': str(wht),
        'operation_datetime': date,
        'settlement_date': date,
    }


# ---------------------------------------------------------------------------
# Sells parser
# ---------------------------------------------------------------------------

def _parse_sells(lines: list[str]) -> list[dict]:
    """Parse 'Sells' data lines."""
    rows = []
    in_table = False

    for line in lines:
        if 'Date acquired' in line and 'Date sold' in line:
            in_table = True
            continue

        if not in_table:
            continue

        if 'PLN' in line or line.strip().startswith('Rate:'):
            continue

        if line.strip().startswith('Total'):
            in_table = False
            continue

        row = _parse_sell_line(line)
        if row:
            rows.append(row)

    return rows


def _parse_sell_line(line: str) -> dict | None:
    """Parse one sell data line.

    Format: {date_acquired} {date_sold} {symbol} {name} {isin} {country} {qty} {cost} {proceeds} {pnl} {fees}
    """
    isin_m = _ISIN_RE.search(line)
    if not isin_m:
        return None

    before = line[:isin_m.start()].strip()
    after = line[isin_m.end():].strip()
    isin = isin_m.group(1)

    parts = before.split()
    if len(parts) < 3:
        return None

    if not (_DATE_RE.match(parts[0]) and _DATE_RE.match(parts[1])):
        return None

    date_sold = parts[1]
    symbol = parts[2]

    after_parts = after.split()
    country = after_parts[0] if after_parts else ''

    amounts = _AMOUNT_RE.findall(after)
    if len(amounts) < 2:
        return None

    currency_char = amounts[0][0]
    currency = _CURRENCY_SYMBOLS.get(currency_char, 'USD')
    gross_proceeds = Decimal(amounts[1][1].replace(',', ''))

    qty = ''
    for token in after_parts[1:]:
        if re.match(r'^[\d,]+\.?\d*$', token):
            qty = token.replace(',', '')
            break

    commission = Decimal('0')
    if len(amounts) >= 3:
        commission = Decimal(amounts[-1][1].replace(',', ''))

    tx_id = hashlib.sha1(
        f'{date_sold}:{symbol}:{isin}:{gross_proceeds}'.encode()
    ).hexdigest()[:16]

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'direction': 'SELL',
        'symbol': symbol,
        'isin': isin,
        'country': country,
        'currency': currency,
        'price': '',
        'quantity': qty,
        'amount': str(gross_proceeds),
        'commission': str(commission),
        'operation_datetime': date_sold,
        'settlement_date': date_sold,
    }


def _write_csv(outfile, rows: list[dict]) -> None:
    writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Convert Revolut Securities PDF P&L statement to CSV')
    parser.add_argument('input', help='Input Revolut Securities .pdf file')
    parser.add_argument('--trades-output', help='Output trades CSV')
    parser.add_argument('--income-output', help='Output income CSV')

    args = parser.parse_args()

    trade_rows, income_rows = convert_revolut(args.input)
    stem = Path(args.input).stem
    suffix = os.urandom(3).hex()

    if trade_rows:
        trades_path = args.trades_output or f'result_trades_{stem}_{suffix}.csv'
        with open(trades_path, 'w') as f:
            _write_csv(f, trade_rows)
        print(f"Wrote {len(trade_rows)} trade(s) → {trades_path}")

    if income_rows:
        income_path = args.income_output or f'result_income_{stem}_{suffix}.csv'
        with open(income_path, 'w') as f:
            _write_csv(f, income_rows)
        print(f"Wrote {len(income_rows)} income record(s) → {income_path}")


if __name__ == '__main__':
    main()

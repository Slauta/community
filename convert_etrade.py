#!/usr/bin/env python3

# /// script
# requires-python = ">=3.12"
# dependencies = [
# ]
# ///

import argparse
import csv
import hashlib
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TextIO


BROKER = 'ETRADE'


def convert_etrade(infile: TextIO) -> tuple[list[dict], list[dict]]:
    """Convert E*TRADE CSV transaction report.

    Columns: TransactionDate, Type, Description, Symbol, Quantity,
             Price, Commission, Amount, NetProceeds

    Returns:
        Tuple of (trade_rows, income_rows).
    """
    trade_rows = []
    income_rows = []

    for row in csv.DictReader(infile):
        tx_type = row['Type'].strip()

        if tx_type in ('Bought', 'Sold'):
            trade_rows.append(_convert_trade(row))
        elif tx_type == 'Dividend':
            income_rows.append(_convert_dividend(row))

    return trade_rows, income_rows


def _parse_date(s: str) -> str:
    """Parse 'MM/DD/YY' → ISO date string."""
    return datetime.strptime(s.strip(), '%m/%d/%y').date().isoformat()


def _decimal(s: str) -> Decimal:
    s = s.strip().replace(',', '')
    return Decimal(s) if s else Decimal('0')


def _convert_trade(row: dict) -> dict:
    direction = 'BUY' if row['Type'].strip() == 'Bought' else 'SELL'
    symbol = row['Symbol'].strip()
    date = _parse_date(row['TransactionDate'])
    quantity = row['Quantity'].strip()
    price = str(_decimal(row['Price']))
    commission = str(_decimal(row['Commission']))
    amount = str(abs(_decimal(row['Amount'])))

    tx_id = hashlib.sha1(
        f'{date}:{direction}:{symbol}:{amount}'.encode()
    ).hexdigest()[:16]

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'direction': direction,
        'symbol': symbol,
        'isin': '',
        'country': 'US',
        'currency': 'USD',
        'price': price,
        'quantity': quantity,
        'amount': amount,
        'commission': commission,
        'operation_datetime': date,
        'settlement_date': date,
    }


def _convert_dividend(row: dict) -> dict:
    symbol = row['Symbol'].strip()
    date = _parse_date(row['TransactionDate'])
    gross_amount = str(_decimal(row['Amount']))
    tx_id = f'{symbol}:DIV:{date}'

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'income_type': 'DIVIDEND',
        'symbol': symbol,
        'currency': 'USD',
        'gross_amount': gross_amount,
        'wht_amount': '0',
        'operation_datetime': date,
        'settlement_date': date,
    }


def _write_csv(outfile: TextIO, rows: list[dict]) -> None:
    writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Convert E*TRADE CSV transaction report to CSV')
    parser.add_argument('input', type=argparse.FileType('r'), help='Input E*TRADE CSV file')
    parser.add_argument('--trades-output', help='Output trades CSV')
    parser.add_argument('--income-output', help='Output income CSV')

    args = parser.parse_args()

    trade_rows, income_rows = convert_etrade(args.input)
    args.input.close()

    stem = Path(args.input.name).stem
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

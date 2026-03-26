import csv
import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import TextIO


BROKER = 'SCHWAB'


def _parse_amount(s):
    """Parse '$1,234.56' or '-$1,234.56' -> Decimal. Empty string -> 0."""
    s = s.strip().replace('$', '').replace(',', '')
    return Decimal(s) if s else Decimal('0')


def _parse_date(s):
    """Parse Schwab date string -> (operation_date, settlement_date).

    '12/30/2025'                   -> (2025-12-30, 2025-12-30)
    '12/16/2024 as of 12/15/2024'  -> (2025-12-15, 2025-12-16)
    """
    s = s.strip()
    if ' as of ' in s:
        recorded_str, actual_str = s.split(' as of ')
        operation = datetime.strptime(actual_str.strip(), '%m/%d/%Y').date()
        settlement = datetime.strptime(recorded_str.strip(), '%m/%d/%Y').date()
    else:
        operation = datetime.strptime(s, '%m/%d/%Y').date()
        settlement = operation
    return operation, settlement


def _tx_id(*parts):
    """Deterministic 16-char hex ID from the given parts."""
    raw = '|'.join(str(p) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def convert_schwab(infile):
    rows = list(csv.DictReader(infile))

    # First pass: accumulate withholding tax by (symbol, operation_date)
    # NRA Tax Adj and Foreign Tax Paid carry negative amounts = tax withheld.
    wht_map = {}
    for row in rows:
        action = row['Action'].strip()
        if action in ('NRA Tax Adj', 'Foreign Tax Paid'):
            symbol = row['Symbol'].strip()
            op_date, _ = _parse_date(row['Date'])
            wht_map[(symbol, op_date)] = (
                wht_map.get((symbol, op_date), Decimal('0'))
                + abs(_parse_amount(row['Amount']))
            )

    trade_rows = []
    income_rows = []

    for row in rows:
        action = row['Action'].strip()

        if action in ('Buy', 'Sell'):
            trade_rows.append(_convert_trade(row))

        elif action == 'Qualified Dividend':
            income_rows.append(_convert_dividend(row, wht_map))

        elif action == 'Credit Interest':
            income_rows.append(_convert_interest(row))

        # Skip: NRA Tax Adj, Foreign Tax Paid (consumed above),
        #        ADR Mgmt Fee, Wire Received, Stock Merger

    return trade_rows, income_rows


def _convert_trade(row):
    action = row['Action'].strip()
    direction = 'BUY' if action == 'Buy' else 'SELL'

    symbol = row['Symbol'].strip()
    op_date, settlement = _parse_date(row['Date'])
    quantity = row['Quantity'].strip().replace(',', '')
    price = _parse_amount(row['Price'])
    commission = _parse_amount(row['Fees & Comm'])
    net_amount = abs(_parse_amount(row['Amount']))

    # Gross amount before commission:
    #   SELL: net proceeds = gross - commission  =>  gross = net + commission
    #   BUY:  total paid   = gross + commission  =>  gross = net - commission
    if direction == 'SELL':
        gross_amount = net_amount + commission
    else:
        gross_amount = net_amount - commission

    tx_id = _tx_id(BROKER, op_date, action, symbol, quantity, row['Amount'].strip())

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'direction': direction,
        'symbol': symbol,
        'isin': '',
        'country': 'US',
        'currency': 'USD',
        'price': str(price),
        'quantity': quantity,
        'amount': str(gross_amount),
        'commission': str(commission),
        'operation_datetime': op_date.isoformat(),
        'settlement_date': settlement.isoformat(),
    }


def _convert_dividend(row, wht_map):
    symbol = row['Symbol'].strip()
    op_date, settlement = _parse_date(row['Date'])
    gross_amount = _parse_amount(row['Amount'])
    wht_amount = wht_map.get((symbol, op_date), Decimal('0'))

    tx_id = _tx_id(BROKER, op_date, 'DIVIDEND', symbol, row['Amount'].strip())

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'income_type': 'DIVIDEND',
        'symbol': symbol,
        'currency': 'USD',
        'gross_amount': str(gross_amount),
        'wht_amount': str(wht_amount),
        'operation_datetime': op_date.isoformat(),
        'settlement_date': settlement.isoformat(),
    }


def _convert_interest(row):
    op_date, settlement = _parse_date(row['Date'])
    gross_amount = _parse_amount(row['Amount'])
    tx_id = _tx_id(BROKER, op_date, 'INTEREST', row['Amount'].strip())

    return {
        'broker': BROKER,
        'tx_id': tx_id,
        'income_type': 'INTEREST',
        'symbol': 'USD-INT',
        'currency': 'USD',
        'gross_amount': str(gross_amount),
        'wht_amount': '0',
        'operation_datetime': op_date.isoformat(),
        'settlement_date': settlement.isoformat(),
    }

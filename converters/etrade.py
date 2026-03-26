import csv
import hashlib
from datetime import datetime
from decimal import Decimal
from typing import TextIO


BROKER = 'ETRADE'


def convert_etrade(infile: TextIO):
    """Convert E*TRADE CSV transaction report.

    Columns: TransactionDate, Type, Description, Symbol, Quantity,
             Price, Commission, Amount, NetProceeds
    Returns (trade_rows, income_rows).
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


def _parse_date(s):
    """Parse 'MM/DD/YY' → ISO date string."""
    return datetime.strptime(s.strip(), '%m/%d/%y').date().isoformat()


def _decimal(s):
    s = s.strip().replace(',', '')
    return Decimal(s) if s else Decimal('0')


def _convert_trade(row):
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


def _convert_dividend(row):
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

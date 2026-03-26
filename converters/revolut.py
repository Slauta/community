import re
from decimal import Decimal

import pdfplumber


BROKER = 'Revolut'

_CURRENCY_SYMBOLS = {'€': 'EUR', '$': 'USD', '£': 'GBP'}
_ISIN_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{10})\b')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_AMOUNT_RE = re.compile(r'(?:US)?([€$£])([\d,]+\.?\d*)')


def convert_revolut(pdf_path):
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

def _is_sells_detail(lines):
    """Sells detail page has 'Date acquired' column header."""
    return any('Date acquired' in l and 'Date sold' in l for l in lines)


def _is_income_detail(lines):
    """Income detail page has 'Date Description' column header."""
    return any('Date' in l and 'Description' in l and 'ISIN' in l for l in lines)


# ---------------------------------------------------------------------------
# Income parser
# ---------------------------------------------------------------------------

def _parse_income(lines):
    """Parse 'Other income & fees' data lines."""
    rows = []
    in_table = False

    for line in lines:
        # Table starts after column header row
        if 'Date' in line and 'Description' in line and 'ISIN' in line:
            in_table = True
            continue

        if not in_table:
            continue

        # Skip PLN conversion lines and rate lines
        if line.strip().startswith('Rate:') or 'PLN' in line:
            continue

        # Stop at totals
        if line.strip().startswith('Total'):
            in_table = False
            continue

        row = _parse_income_line(line)
        if row:
            rows.append(row)

    return rows


def _parse_income_line(line):
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
    # Text after country: "{gross} - {net}"  or  "{gross} {wht} {net}"
    # Check whether a bare '-' appears between the first and last amount.
    first_amount_end = after.index(gross_str) + len(gross_str)
    between = after[first_amount_end:]
    wht = Decimal('0')
    if re.search(r'(?<!\d)-(?!\d)', between.split(_AMOUNT_RE.search(between).group())[0]):
        wht = Decimal('0')  # dash = no WHT
    elif len(amounts) >= 3:
        wht = Decimal(amounts[1][1].replace(',', ''))  # explicit WHT amount

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

def _parse_sells(lines):
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


def _parse_sell_line(line):
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

    date_acquired = parts[0]
    date_sold = parts[1]
    symbol = parts[2]

    after_parts = after.split()
    country = after_parts[0] if after_parts else ''

    amounts = _AMOUNT_RE.findall(after)
    if len(amounts) < 2:
        return None

    currency_char = amounts[0][0]
    currency = _CURRENCY_SYMBOLS.get(currency_char, 'USD')
    cost_basis = Decimal(amounts[0][1].replace(',', ''))
    gross_proceeds = Decimal(amounts[1][1].replace(',', ''))

    # Quantity is the first numeric token after country
    qty = ''
    for token in after_parts[1:]:
        if re.match(r'^[\d,]+\.?\d*$', token):
            qty = token.replace(',', '')
            break

    # Commission is the last amount (if not '-')
    commission = Decimal('0')
    if len(amounts) >= 3:
        commission = Decimal(amounts[-1][1].replace(',', ''))

    tx_id = hashlib.sha1(f'{date_sold}:{symbol}:{isin}:{gross_proceeds}'.encode()).hexdigest()[:16]

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

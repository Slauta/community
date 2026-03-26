from datetime import datetime


BROKER = 'BUNQ'


def convert_bunq(infile):
    """Convert bunq CSV to (trade_rows, income_rows).

    bunq only produces income (interest), so trade_rows is always empty.
    """
    import csv

    reader = csv.DictReader(infile)
    income_rows = []

    for row in reader:
        description = row['Description'].strip()

        # Filter for interest payments only
        if 'bunq Payday' not in description:
            continue

        operation_datetime = datetime.strptime(row['Date'].strip(), '%Y-%m-%d')
        settlement_date = operation_datetime.date()

        # Parse amount (remove thousands separator)
        amount_str = row['Amount'].strip().replace(',', '')

        # Extract currency from description: "bunq Payday 2026-01-25 EUR"
        currency = description.split()[-1]

        symbol = f"{currency}-INT"
        income_rows.append({
            'broker': BROKER,
            'tx_id': f"{symbol}:{settlement_date.isoformat()}",
            'income_type': 'INTEREST',
            'symbol': symbol,
            'currency': currency,
            'gross_amount': amount_str,
            'wht_amount': '0',
            'operation_datetime': operation_datetime.isoformat(),
            'settlement_date': settlement_date.isoformat(),
        })

    return [], income_rows

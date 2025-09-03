# tracker.py
import csv
import requests
import yfinance as yf
from collections import defaultdict
from datetime import datetime
from tabulate import tabulate
from typing import IO
from io import StringIO

from utils import round2, percent, format_in_indian_system, parse_indian_value
from storage import get_storage_backend

def get_portfolio_summary(backend=None, filename="transactions.csv") -> str:
    backend = backend or get_storage_backend()
    header, rows = backend.load_csv(filename)

    if not header or not rows:
        return "⚠️ No data found in transaction file."

    csv_content = ",".join(header) + "\n" + "\n".join([",".join(row) for row in rows])
    return generate_summary(read_transactions(StringIO(csv_content)))


def read_transactions(file_obj: IO):
    transactions = defaultdict(list)
    reader = csv.DictReader(file_obj)
    for row in reader:
        scheme_code = row['scheme_code']
        transactions[scheme_code].append({
            'date': row['date'],
            'scheme_name': row['scheme_name'],
            'nav': float(row['nav']),
            'units': float(row['units']),
            'type': row.get('type', 'buy').lower(),
            'asset_type': row.get('asset_type', 'mutual_fund')  # default if missing
        })
    return transactions


def fetch_latest_price(asset_type, scheme_code):
    try:
        if asset_type == 'mutual_fund':
            url = f"https://api.mfapi.in/mf/{scheme_code}/latest"
            response = requests.get(url, timeout=10)
            data = response.json()
            return float(data['data'][0]['nav'])

        elif asset_type in ('indian_equity', 'aus_equity'):
            ticker = yf.Ticker(scheme_code)
            price = ticker.history(period='1d')['Close'][-1]
            return float(price)

        else:
            print(f"Unknown asset_type: {asset_type}")
            return None
    except Exception as e:
        print(f"Error fetching price for {scheme_code} ({asset_type}): {e}")
        return None


def xirr(cash_flows, max_iterations=100, tolerance=1e-6):
    def xnpv(rate):
        return sum(cf / (1 + rate) ** ((date - cash_flows[0][0]).days / 365.0) for date, cf in cash_flows)

    low, high = -0.9999, 10
    for _ in range(max_iterations):
        mid = (low + high) / 2
        npv = xnpv(mid)
        if abs(npv) < tolerance:
            return mid
        if npv > 0:
            low = mid
        else:
            high = mid
    return None


def generate_summary(transactions):
    today = datetime.today()
    total_portfolio_value = 0
    latest_prices = {}

    total_invested = 0
    total_current = 0
    total_realized = 0
    total_unrealized = 0

    # First Pass — fetch latest prices and compute total portfolio value
    for scheme_code, txns in transactions.items():
        asset_type = txns[0]['asset_type']
        latest_price = fetch_latest_price(asset_type, scheme_code)
        if latest_price is None:
            continue
        net_units = sum(t['units'] if t['type'] == 'buy' else -t['units'] for t in txns)
        total_portfolio_value += net_units * latest_price
        latest_prices[scheme_code] = latest_price

    output_rows = []

    for scheme_code, txns in transactions.items():
        scheme_name = txns[0]['scheme_name']
        asset_type = txns[0]['asset_type']
        latest_price = latest_prices.get(scheme_code)
        if latest_price is None:
            continue

        net_units = 0
        invested = 0
        realized_pl = 0
        cash_flows = []
        navs = []
        buy_lots = []

        for t in sorted(txns, key=lambda x: x['date']):
            date = datetime.strptime(t['date'], "%d-%m-%Y")
            nav = t['nav']
            units = t['units']
            tx_type = t['type']

            if tx_type == 'buy':
                net_units += units
                invested += nav * units
                buy_lots.append({'units': units, 'nav': nav})
                cash_flows.append((date, -nav * units))
                navs.append(nav)
            elif tx_type == 'sell':
                net_units -= units
                cash_flows.append((date, nav * units))
                remaining_to_sell = units
                while remaining_to_sell > 0 and buy_lots:
                    lot = buy_lots[0]
                    if lot['units'] <= remaining_to_sell:
                        gain = (nav - lot['nav']) * lot['units']
                        realized_pl += gain
                        remaining_to_sell -= lot['units']
                        buy_lots.pop(0)
                    else:
                        gain = (nav - lot['nav']) * remaining_to_sell
                        realized_pl += gain
                        lot['units'] -= remaining_to_sell
                        remaining_to_sell = 0

        current_value = net_units * latest_price
        unrealized_pl = current_value - sum(lot['units'] * lot['nav'] for lot in buy_lots)

        total_invested += invested
        total_current += current_value
        total_realized += realized_pl
        total_unrealized += unrealized_pl

        avg_nav = (sum(lot['units'] * lot['nav'] for lot in buy_lots) / net_units) if net_units else 0
        pct_change = ((latest_price - avg_nav) / avg_nav * 100) if avg_nav else 0
        pct_portfolio = (current_value / total_portfolio_value * 100) if total_portfolio_value else 0
        min_nav = min(navs) if navs else 0
        max_nav = max(navs) if navs else 0

        cash_flows.append((today, current_value))
        rate = xirr(cash_flows)
        xirr_result = percent(rate * 100) if rate else "N/A"

        output_rows.append([
            scheme_name,
            round2(latest_price),
            round2(net_units),
            format_in_indian_system(invested),
            format_in_indian_system(current_value),
            format_in_indian_system(realized_pl),
            format_in_indian_system(unrealized_pl),
            round2(avg_nav),
            percent(pct_change),
            percent(pct_portfolio),
            xirr_result,
            f"{min_nav:,.2f}",
            f"{max_nav:,.2f}"
        ])

    # Append Total row
    output_rows.append([
        "**Total**", "", "", 
        format_in_indian_system(total_invested),
        format_in_indian_system(total_current),
        format_in_indian_system(total_realized),
        format_in_indian_system(total_unrealized),
        "", "", "", "", "", ""
    ])

    headers = [
        "Fund", "Latest Price", "Units", "Invested ₹", "Current ₹",
        "Realized P/L", "Unrealized P/L", "Avg Purchase NAV",
        "% Return", "% Portfolio", "XIRR", "Min NAV", "Max NAV"
    ]

    output_rows.sort(key=lambda row: parse_indian_value(row[3]), reverse=True)
    summary_str = "\n📊 Portfolio Summary:\n\n" + tabulate(output_rows, headers=headers, tablefmt="grid")
    return summary_str

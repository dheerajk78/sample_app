# tracker.py
import csv
import requests
import yfinance as yf
from collections import defaultdict
from datetime import datetime
from tabulate import tabulate
from typing import IO
from io import StringIO
from bs4 import BeautifulSoup

from utils import round2, percent, format_in_indian_system, parse_indian_value
from storage import get_storage_backend

def get_portfolio_summary(backend=None, filename="transactions.csv") -> str:
    backend = backend or get_storage_backend()
    header, rows = backend.load_csv(filename)

    if not header or not rows:
        return "⚠️ No data found in transaction file."

    csv_content = ",".join(header) + "\n" + "\n".join([",".join(row) for row in rows])
    return generate_summary_html(read_transactions(StringIO(csv_content)))


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
            hist = ticker.history(period="5d")
            if not hist.empty:
                return float(hist["Close"][-1])
            
            # fallback scrape
            price = fetch_price_yahoo_fallback(scheme_code)
            if price:
                return price

            print(f"[YahooFinance] No price data found for {scheme_code}")

        else:
            print(f"Unknown asset_type: {asset_type}")
            return None
    except Exception as e:
        print(f"Error fetching price for {scheme_code} ({asset_type}): {e}")
        return None

def fetch_price_yahoo_fallback(symbol):
    url = f"https://au.finance.yahoo.com/quote/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the span that holds the current price (this selector may change over time)
    price_span = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
    if price_span:
        try:
            price = float(price_span.text.replace(',', ''))
            return price
        except Exception:
            pass
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

def format_currency(value, asset_type):
    if asset_type in ('mutual_fund', 'indian_equity'):
        return format_in_indian_system(value)
    elif asset_type == 'aus_equity':
        return format_in_aud_system(value)
    else:
        return f"{value:,.2f}"
        
def generate_summary_html(transactions):
    today = datetime.today()
    latest_navs = {}
    grouped_data = defaultdict(list)
    totals_by_type = defaultdict(lambda: {
        "invested": 0, "current": 0, "realized": 0,
        "unrealized": 0, "portfolio_value": 0
    })

    # Pre-fetch NAVs and compute total portfolio value
    total_portfolio_value = 0
    for scheme_code, txns in transactions.items():
        asset_type = txns[0].get('asset_type', 'unknown')
        scheme_code = scheme_code.strip()
        latest_nav = fetch_latest_price(asset_type, scheme_code)
        if latest_nav is None:
            continue
        net_units = sum(t['units'] if t['type'] == 'buy' else -t['units'] for t in txns)
        total_portfolio_value += net_units * latest_nav
        latest_navs[scheme_code] = latest_nav

    # Process each scheme
    for scheme_code, txns in transactions.items():
        asset_type = txns[0].get('asset_type', 'unknown')
        scheme_name = txns[0]['scheme_name']
        latest_nav = latest_navs.get(scheme_code.strip())
        if latest_nav is None:
            continue

        net_units, invested, realized_pl = 0, 0, 0
        cash_flows, navs, buy_lots = [], [], []

        for t in sorted(txns, key=lambda x: x['date']):
            date = datetime.strptime(t['date'], "%d-%m-%Y")
            nav, units, tx_type = t['nav'], t['units'], t['type']

            if tx_type == 'buy':
                net_units += units
                invested += nav * units
                buy_lots.append({'units': units, 'nav': nav})
                cash_flows.append((date, -nav * units))
                navs.append(nav)
            elif tx_type == 'sell':
                net_units -= units
                cash_flows.append((date, nav * units))
                remaining = units
                while remaining > 0 and buy_lots:
                    lot = buy_lots[0]
                    if lot['units'] <= remaining:
                        realized_pl += (nav - lot['nav']) * lot['units']
                        remaining -= lot['units']
                        buy_lots.pop(0)
                    else:
                        realized_pl += (nav - lot['nav']) * remaining
                        lot['units'] -= remaining
                        remaining = 0

        current_value = net_units * latest_nav
        unrealized_pl = current_value - sum(lot['units'] * lot['nav'] for lot in buy_lots)
        totals = totals_by_type[asset_type]
        totals["invested"] += invested
        totals["current"] += current_value
        totals["realized"] += realized_pl
        totals["unrealized"] += unrealized_pl
        totals["portfolio_value"] += current_value

        avg_nav = (sum(lot['units'] * lot['nav'] for lot in buy_lots) / net_units) if net_units else 0
        pct_change = ((latest_nav - avg_nav) / avg_nav * 100) if avg_nav else 0
        pct_portfolio = (current_value / total_portfolio_value * 100) if total_portfolio_value else 0
        min_nav, max_nav = min(navs, default=0), max(navs, default=0)

        cash_flows.append((today, current_value))
        rate = xirr(cash_flows)
        xirr_result = percent(rate * 100) if rate else "N/A"

        grouped_data[asset_type].append({
            "scheme_name": scheme_name,
            "latest_nav": round2(latest_nav),
            "units": round2(net_units),
            "invested": invested,
            "current_value": current_value,
            "realized_pl": realized_pl,
            "unrealized_pl": unrealized_pl,
            "avg_nav": round2(avg_nav),
            "pct_change": percent(pct_change),
            "pct_portfolio": percent(pct_portfolio),
            "xirr": xirr_result,
            "min_nav": f"{min_nav:,.2f}",
            "max_nav": f"{max_nav:,.2f}",
            "scheme_code": scheme_code
        })

    # Generate HTML
    html = "<h2>📊 Portfolio Summary</h2>\n"
    for asset_type, rows in grouped_data.items():
        totals = totals_by_type[asset_type]
        currency = "₹" if asset_type in ('mutual_fund', 'indian_equity') else "A$"
        html += f"<h3>{asset_type.replace('_', ' ').title()}</h3>\n"

        # Summary table
        html += "<table border='1' cellpadding='5' cellspacing='0'>\n<thead><tr>"
        headers = ["Fund", "Latest NAV", "Units", f"Invested {currency}", f"Current {currency}",
                   "Realized P/L", "Unrealized P/L", "Avg Purchase NAV", "% Return", "% Portfolio", "XIRR", "Min NAV", "Max NAV"]
        for col in headers:
            html += f"<th>{escape(col)}</th>"
        html += "</tr></thead>\n<tbody>"

        for row in sorted(rows, key=lambda r: r["invested"], reverse=True):
            html += "<tr>"
            html += f"<td>{escape(row['scheme_name'])}</td>"
            html += f"<td>{row['latest_nav']}</td>"
            html += f"<td>{row['units']}</td>"
            html += f"<td>{format_currency(row['invested'], asset_type)}</td>"
            html += f"<td>{format_currency(row['current_value'], asset_type)}</td>"
            html += f"<td>{format_currency(row['realized_pl'], asset_type)}</td>"
            html += f"<td>{format_currency(row['unrealized_pl'], asset_type)}</td>"
            html += f"<td>{row['avg_nav']}</td>"
            html += f"<td>{row['pct_change']}</td>"
            html += f"<td>{row['pct_portfolio']}</td>"
            html += f"<td>{row['xirr']}</td>"
            html += f"<td>{row['min_nav']}</td>"
            html += f"<td>{row['max_nav']}</td>"
            html += "</tr>"

        html += "<tr style='font-weight: bold; background-color: #f0f0f0;'>"
        html += f"<td>Total</td><td colspan='2'></td>"
        html += f"<td>{format_currency(totals['invested'], asset_type)}</td>"
        html += f"<td>{format_currency(totals['current'], asset_type)}</td>"
        html += f"<td>{format_currency(totals['realized'], asset_type)}</td>"
        html += f"<td>{format_currency(totals['unrealized'], asset_type)}</td>"
        html += "<td colspan='6'></td></tr>"

        html += "</tbody></table><br>"

    return html


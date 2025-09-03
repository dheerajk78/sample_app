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
from markupsafe import escape
import html

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
        symbol="A$"
        return f"{symbol}{value:,.2f}" 
    else:
        return f"{value:,.2f}"
        
def generate_summary_html(transactions):
    today = datetime.today()
    total_portfolio_value = 0
    latest_navs = {}

    grouped_output = defaultdict(list)
    totals_by_type = defaultdict(lambda: {
        "invested": 0, "current": 0, "realized": 0,
        "unrealized": 0, "portfolio_value": 0
    })

    # 1. Calculate total portfolio value
    for scheme_code, txns in transactions.items():
        asset_type = txns[0].get("asset_type", "unknown")
        latest_nav = fetch_latest_price(asset_type, scheme_code.strip())
        if latest_nav is None:
            continue
        net_units = sum(t["units"] if t["type"] == "buy" else -t["units"] for t in txns)
        total_portfolio_value += net_units * latest_nav
        latest_navs[scheme_code] = latest_nav

    # 2. Build tables per asset type
    for scheme_code, txns in transactions.items():
        asset_type = txns[0].get("asset_type", "unknown")
        scheme_name = html.escape(txns[0]["scheme_name"])
        latest_nav = latest_navs.get(scheme_code)
        if latest_nav is None:
            continue

        net_units = 0
        invested = 0
        realized_pl = 0
        cash_flows = []
        navs = []
        buy_lots = []

        for t in sorted(txns, key=lambda x: x["date"]):
            date = datetime.strptime(t["date"], "%d-%m-%Y")
            nav = t["nav"]
            units = t["units"]
            tx_type = t["type"]

            if tx_type == "buy":
                net_units += units
                invested += nav * units
                buy_lots.append({"units": units, "nav": nav})
                cash_flows.append((date, -nav * units))
                navs.append(nav)
            elif tx_type == "sell":
                net_units -= units
                cash_flows.append((date, nav * units))
                remaining = units
                while remaining > 0 and buy_lots:
                    lot = buy_lots[0]
                    if lot["units"] <= remaining:
                        realized_pl += (nav - lot["nav"]) * lot["units"]
                        remaining -= lot["units"]
                        buy_lots.pop(0)
                    else:
                        realized_pl += (nav - lot["nav"]) * remaining
                        lot["units"] -= remaining
                        remaining = 0

        current_value = net_units * latest_nav
        unrealized_pl = current_value - sum(lot["units"] * lot["nav"] for lot in buy_lots)

        # Totals
        totals_by_type[asset_type]["invested"] += invested
        totals_by_type[asset_type]["current"] += current_value
        totals_by_type[asset_type]["realized"] += realized_pl
        totals_by_type[asset_type]["unrealized"] += unrealized_pl
        totals_by_type[asset_type]["portfolio_value"] += current_value

        avg_nav = sum(lot["units"] * lot["nav"] for lot in buy_lots) / net_units if net_units else 0
        pct_change = ((latest_nav - avg_nav) / avg_nav * 100) if avg_nav else 0
        pct_portfolio = (current_value / total_portfolio_value * 100) if total_portfolio_value else 0
        min_nav = min(navs) if navs else 0
        max_nav = max(navs) if navs else 0

        cash_flows.append((today, current_value))
        rate = xirr(cash_flows)
        xirr_result = percent(rate * 100) if rate else "N/A"

        # Currency symbol
        currency = "A$" if asset_type == "aus_equity" else "₹"

        grouped_output[asset_type].append(f"""
        <tr>
            <td>{scheme_name}</td>
            <td>{round2(latest_nav)}</td>
            <td>{round2(net_units)}</td>
            <td>{currency}{format_in_indian_system(invested)[1:]}</td>
            <td>{currency}{format_in_indian_system(current_value)[1:]}</td>
            <td>{currency}{format_in_indian_system(realized_pl)[1:]}</td>
            <td>{currency}{format_in_indian_system(unrealized_pl)[1:]}</td>
            <td>{round2(avg_nav)}</td>
            <td>{percent(pct_change)}</td>
            <td>{percent(pct_portfolio)}</td>
            <td>{xirr_result}</td>
            <td>{min_nav:,.2f}</td>
            <td>{max_nav:,.2f}</td>
        </tr>
        """)

    # 3. Build final HTML string
    html_output = ""

    for asset_type, rows in grouped_output.items():
        currency = "A$" if asset_type == "aus_equity" else "₹"
        total = totals_by_type[asset_type]
        html_output += f"""
<details open>
  <summary><strong>{asset_type.replace('_', ' ').title()}</strong></summary>
  <table border="1" cellpadding="5" cellspacing="0" style="margin-top:10px;">
    <thead>
      <tr>
        <th>Fund</th><th>Latest NAV</th><th>Units</th><th>Invested {currency}</th>
        <th>Current {currency}</th><th>Realized P/L</th><th>Unrealized P/L</th>
        <th>Avg NAV</th><th>% Return</th><th>% Portfolio</th><th>XIRR</th><th>Min NAV</th><th>Max NAV</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
      <tr style="font-weight:bold;">
        <td>Total</td><td colspan="2"></td>
        <td>{currency}{format_in_indian_system(total["invested"])[1:]}</td>
        <td>{currency}{format_in_indian_system(total["current"])[1:]}</td>
        <td>{currency}{format_in_indian_system(total["realized"])[1:]}</td>
        <td>{currency}{format_in_indian_system(total["unrealized"])[1:]}</td>
        <td colspan="6"></td>
      </tr>
    </tbody>
  </table>
</details>
<br>
"""
    return html_output

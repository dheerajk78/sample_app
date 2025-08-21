import csv
import requests
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from tabulate import tabulate
from collections import defaultdict
from typing import TextIO
#from xirr import xirr as xirr_calc

def get_portfolio_summary(file_obj: TextIO) -> str:
    transactions = read_transactions(file_obj)
    return generate_summary(transactions)
    
# ==== UTILS ====
def round2(x):
    return float(Decimal(x).quantize(Decimal('0.01')))

def percent(x):
    return f"{round2(x)}%"

# ==== XIRR ====
#def xirr(cash_flows, guess=0.1):
#    from scipy.optimize import newton
#
#    def xnpv(rate):
#        return sum(cf / (1 + rate) ** ((date - cash_flows[0][0]).days / 365.0)
#                   for date, cf in cash_flows)
##
#    try:
#        return newton(xnpv, guess)
#    except Exception:
#        return None


def xirr(cash_flows):
    # xirr package expects dict: {datetime: amount}
    cf_dict = {dt: amt for dt, amt in cash_flows}
    return xirr_calc(cf_dict)

def xirr(cash_flows, max_iterations=100, tolerance=1e-6):
    def xnpv(rate):
        return sum(cf / (1 + rate) ** ((date - cash_flows[0][0]).days / 365.0)
                   for date, cf in cash_flows)

    low = -0.9999  # Just above -100%
    high = 10      # 1000% max upper bound
    for _ in range(max_iterations):
        mid = (low + high) / 2
        npv = xnpv(mid)
        if abs(npv) < tolerance:
            return mid
        if npv > 0:
            low = mid
        else:
            high = mid
    return None  # Didn't converge


# ==== LOAD TRANSACTIONS ====
def read_transactions(file_obj):
    transactions = defaultdict(list)
    reader = csv.DictReader(file_obj)
    for row in reader:
        print("Fieldnames:", reader.fieldnames)
        scheme_code = row['scheme_code']
        transactions[scheme_code].append({
            'date': row['date'],
            'scheme_name': row['scheme_name'],
            'nav': float(row['nav']),
            'units': float(row['units']),
            'type': row.get('type', 'buy').lower()
        })
        print(transactions)
    return transactions
    
# ==== FETCH LATEST NAV ====
def fetch_latest_nav(scheme_code):
    url = f"https://api.mfapi.in/mf/{scheme_code}/latest"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return float(data['data'][0]['nav'])
    except Exception as e:
        print(f"Error fetching NAV for {scheme_code}: {e}")
        return None

# ==== GENERATE SUMMARY ====
def generate_summary(transactions):
    today = datetime.today()
    total_portfolio_value = 0
    latest_navs = {}

    # Preload NAVs and total value
    for scheme_code, txns in transactions.items():
        latest_nav = fetch_latest_nav(scheme_code)
        if latest_nav is None:
            continue
        net_units = sum(t['units'] if t['type'] == 'buy' else -t['units'] for t in txns)
        total_portfolio_value += net_units * latest_nav
        latest_navs[scheme_code] = latest_nav

    output_rows = []

    for scheme_code, txns in transactions.items():
        scheme_name = txns[0]['scheme_name']
        latest_nav = latest_navs.get(scheme_code)
        if latest_nav is None:
            continue

        # Variables
        net_units = 0
        invested = 0
        realized_pl = 0
        cash_flows = []
        navs = []

        # FIFO stack for buy lots
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

        # Remaining investment value
        current_value = net_units * latest_nav
        unrealized_pl = current_value - sum(lot['units'] * lot['nav'] for lot in buy_lots)
        avg_nav = (sum(lot['units'] * lot['nav'] for lot in buy_lots) / net_units) if net_units else 0
        pct_change = ((latest_nav - avg_nav) / avg_nav * 100) if avg_nav else 0
        pct_portfolio = (current_value / total_portfolio_value * 100) if total_portfolio_value else 0

        # Add today's value to cash flows for XIRR
        cash_flows.append((today, current_value))
        rate = xirr(cash_flows)
        xirr_result = percent(rate * 100) if rate else "N/A"

        output_rows.append([
            scheme_name,
            round2(latest_nav),
            round2(net_units),
            round2(invested),
            round2(current_value),
            round2(realized_pl),
            round2(unrealized_pl),
            round2(avg_nav),
            percent(pct_change),
            percent(pct_portfolio),
            xirr_result
        ])

    headers = [
        "Fund", "Latest NAV", "Units", "Invested ₹", "Current ₹",
        "Realized P/L", "Unrealized P/L", "Avg Purchase NAV",
        "% Return", "% Portfolio", "XIRR"
    ]

    print("\n📊 Portfolio Summary:\n")
    print(tabulate(output_rows, headers=headers, tablefmt="grid"))
    summary_str = "\n📊 Portfolio Summary:\n\n" + tabulate(output_rows, headers=headers, tablefmt="grid")
    
    # Instead of print, return the string
    return summary_str

# ==== MAIN ====
if __name__ == "__main__":
    transactions = read_transactions("transactions.csv")
    generate_summary(transactions)

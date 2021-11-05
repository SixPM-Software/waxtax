import calendar
import csv
import datetime
import json
import sys
import time
import os
from pathlib import Path

import requests
import yaml

if len(sys.argv) == 2:
    CONFIG_PATH = Path(sys.argv[1])
else:
    CONFIG_PATH = Path("config.yaml")

with open(CONFIG_PATH, "r") as f:
    try:
        CONFIG = yaml.safe_load(f)
    except:
        print("Invalid config file")
        exit()

EXPORT_FOLDER = Path(CONFIG["export-folder"])
if not os.path.isdir(EXPORT_FOLDER):
    os.mkdir(EXPORT_FOLDER)

endpoint_found = False
for i in CONFIG.get("endpoints", []):
    if requests.get(i).status_code == 200:
        ENDPOINT = i
        print(f"Using endpoint {i}")
        endpoint_found = True
        break
if not endpoint_found:
    print("No functional endpoint found - check config file for endpoints")
    exit(1)

START_DATE = CONFIG.get("date-range", {}).get("start")
END_DATE = CONFIG.get("date-range", {}).get("end")
if not START_DATE or not END_DATE:
    print("Date range incorrectly configured.")
    exit(1)
try:
    datetime.datetime.fromisoformat(START_DATE)
    datetime.datetime.fromisoformat(END_DATE)
except:
    print("Date range incorrectly configured.")
    exit(1)


CURRENCY = CONFIG.get("currency", "")
if not CURRENCY:
    print("Currency to convert to is missing.")
    exit(1)


def dt2ts(dt):
    """Converts a datetime object to UTC timestamp

    naive datetime will be considered UTC.

    """

    return calendar.timegm(dt.utctimetuple())


def main():
    print("WAX Exporter v0.1.0")
    print("Created by SixPM Software")
    print()
    # Get price data for currency
    prices = requests.get(
        f"https://api.coingecko.com/api/v3/coins/wax/market_chart?vs_currency={CURRENCY.lower()}&days=max"
    )
    try:
        history = dict(prices.json()["prices"])
    except:
        print("Currency code not found")
        exit(1)
    else:
        print(f"Retrieved price data for {CURRENCY}")
    print(f"Checking for transactions between {START_DATE} and {END_DATE}")
    wallet_actions = {}
    # Begin transaction loop
    for wallet in CONFIG.get("accounts", []):
        print(f"Starting {wallet}")
        scans = 0
        actions = []
        start = START_DATE
        # NOTE: limit is 1000 to match standard ratelimits across API endpoints
        while True:
            scans += 1
            params = {
                "account": wallet,
                "after": start,
                "before": END_DATE,
                "limit": 1000,
                "sort": "asc",
                "filter": CONFIG.get("contract", "eosio.token:transfer"),
            }
            actions_call = requests.get(ENDPOINT, params=params)
            try:
                new = json.loads(actions_call.content)
                new["actions"]
            except:
                print(actions_call.content)
                print(actions_call.url)
                print(f"ERROR DOWNLOADING DATA: {wallet}, trying again")
                time.sleep(5)
                continue
            actions.extend(new["actions"])
            if len(new["actions"]) < params["limit"]:
                break
            start = new["actions"][-1]["timestamp"]
            print(f"Moving to {start}")
            # delay to respect variable ratelimits between endpoints
            time.sleep(5)
            continue
        filtered = []
        # remove duplicate actions
        for action in actions:
            if action not in filtered:
                filtered.append(action)
        if len(filtered)!=0:    
            print(f"{len(filtered)} actions found, ending at {filtered[-1]['timestamp']}")
            wallet_actions[wallet] = filtered
        else:
            print(f"No actions found between {START_DATE} and {END_DATE}")
            wallet_actions[wallet] = None
    print("Action record fetch from blockchain complete. Exporting records now (if applicable)....")

    # Create CSV files from data
    for wallet in CONFIG.get("accounts", []):
        export_path = EXPORT_FOLDER / (wallet.replace(".", "_") + ".csv")
        with open(export_path, "w+", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "timestamp",
                    "block",
                    "contract",
                    "from",
                    "to",
                    "memo",
                    "wax",
                    "wax_historical",
                    "value_at_date",
                    "trx_id",
                    "data",
                ]
            )
            if wallet_actions[wallet] is not None:
                for action in wallet_actions[wallet]:
                    row = []
                    row.append(str(action["timestamp"]))
                    row.append(str(action["block_num"]))
                    row.append(
                        str(action["act"]["account"]) + " - " + str(action["act"]["name"])
                    )
                    data = action["act"]["data"]
                    row.append(data["from"])
                    row.append(data["to"])
                    row.append(data["memo"])
                    row.append(data["amount"])
                    date = datetime.datetime.fromisoformat(
                        action["timestamp"].split("T")[0]
                    )
                    date = dt2ts(date) * 1000
                    price = history.get(date, False)
                    if price:
                        value = history[date] * float(data["amount"])
                        row.append(f"{CURRENCY.upper()}{round(price,5)}")
                        row.append(f"{round(value,5)}")
                    else:
                        row.append(f"No Data")
                        row.append(f"No Data")
                    row.append(str(action["trx_id"]))
                    row.append(json.dumps(data))
                    writer.writerow(row)
                print("Finished!")
            else:
                print("No records to export. Done.")


if __name__ == "__main__":
    main()

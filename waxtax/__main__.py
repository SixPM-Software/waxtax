import calendar
import csv
import datetime
import json
import os
import random
import sys
import time
from itertools import cycle
from pathlib import Path
from typing import Literal

import click
import requests
import yaml

from plugins.country_codes import check_country_code


def pre_checks(config: dict, mode: Literal["fast", "full"]):
    """Pre check function to create directory and generate endpoint list

    Args:
        config (dict): loaded config from yaml
        mode (fast/full): which mode to use. fast uses a single endpoint, full uses three.
    """
    # can specify config file location in case of multiple data pulls needed
    print("[Pre-Checks] Checking export location")
    export_folder = Path(config["export-folder"])
    if not os.path.isdir(export_folder):
        os.mkdir(export_folder)
        print(f"[Pre-Checks] Created folder `{export_folder}`")
    else:
        print(f"[Pre-Checks] Folder `{export_folder}` found! Using for exports.")

    print(f"[Pre-Checks] Checking endpoints")
    endpoint_request = requests.get(
        "https://validate.eosnation.io/wax/reports/endpoints.json"
    ).json()
    endpoints = endpoint_request["report"]["hyperion_https"]
    endpoints = {e[0]["name"]: e[1] for e in endpoints}
    for bad in config.get("exclude-endpoints"):
        if bad in endpoints:
            del endpoints[bad]

    # shuffle the endpoints to prevent over traffic
    names = list(endpoints.keys())
    random.shuffle(names)
    endpoints = {name: endpoints[name] for name in names}

    if mode.lower() == "full":
        used_endpoints = []
        for name, url in endpoints.items():
            if requests.get(f"{url}/v2/health").status_code == 200:
                print(f"[Pre-Checks] Endpoint {len(used_endpoints)+1}: {name} @ {url}")
                used_endpoints.append(url)
                if len(used_endpoints) == 3:
                    break
        if len(used_endpoints) < 3:
            print("[Pre-Checks] Couldn't find 3 functional endpoints")
            exit()
    elif mode.lower() == "fast":
        endpoint_found = False
        for name, url in endpoints.items():
            if requests.get(f"{url}/v2/health").status_code == 200:
                print(f"[Pre-Checks] Using endpoint {name} @ {url}")
                endpoint_found = True
                used_endpoints = [url]
                break
        if not endpoint_found:
            print(
                "[Pre-Checks] No functional endpoint found - is something wrong with the Blockchain right now?"
            )
            exit(1)
    else:
        print("[Pre-Checks] Invalid mode - must be `fast` or `full`.")
        exit(1)
    return used_endpoints


def dt2ts(dt):
    """Converts a datetime object to UTC timestamp

    naive datetime will be considered UTC.

    """

    return calendar.timegm(dt.utctimetuple())

# Actual main function
@click.command()
@click.option("--country/--no-country", default=False)
def waxtax(country):
    print(
        """┌────────────────────────────────────────────────────┐
│                                                    │
│         WAXTax Transaction Exporter v1.0.1         │
│             Created by SixPM Software              │
│                                                    │
│ WAXtax wouldn't be possible without the incredible │
│ block producer guilds that host the endpoints that │
│     this program obtains data from. Thank you!     │
│                                                    │
└────────────────────────────────────────────────────┘"""
    )

    print()
    print("[WAXTax] Loading configuration")

    # check for country flag
    if country:
        print(
            "[WAXTax] WARNING: Collating Country Code information is a very slow process."
        )
        print(
            "[WAXTax] As in very, very slow. Every transaction needs to be checked individually."
        )
        print(
            "[WAXTax] If you have a high number of drop sales, use a small date range to test timing before exporting a larger dataset."
        )
        choice = input("[WAXTax] Continue [Y/N]: ")
        if choice.lower() != "y":
            print("[WAXTax] Exiting WAXTax")
            exit()

    # load config file
    config_path = Path("config.yaml")
    with open(config_path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except:
            print("Invalid config file")
            exit()
    mode = config["mode"]

    # run startup checks
    print(f"[Pre-Checks] Running WAXtax in {mode} mode.")

    START_DATE = config.get("date-range", {}).get("start")
    END_DATE = config.get("date-range", {}).get("end")
    if not START_DATE or not END_DATE:
        print("[Pre-Checks] Date range incorrectly configured.")
        exit(1)
    try:
        datetime.datetime.fromisoformat(START_DATE)
        datetime.datetime.fromisoformat(END_DATE)
    except:
        print("[Pre-Checks] Date range incorrectly configured.")
        exit(1)

    CURRENCY = config.get("currency", "")
    if not CURRENCY:
        print("[Pre-Checks] Currency to convert to is missing.")
        exit(1)

    endpoints = pre_checks(config=config, mode=mode)
    # Get price data for currency
    prices = requests.get(
        f"https://api.coingecko.com/api/v3/coins/wax/market_chart?vs_currency={CURRENCY.lower()}&days=max"
    )
    try:
        history = dict(prices.json()["prices"])
    except:
        print("[Pre-Checks] Currency code not found")
        exit(1)
    else:
        print(f"[Pre-Checks] Retrieved price data for {CURRENCY}")

    # start getting the data
    print()
    print("[Searching] Beginning data retrieval from the WAX Blockchain")
    print(f"[Searching] Checking for transactions between {START_DATE} and {END_DATE}")
    wallet_actions = {}
    # Begin transaction loop
    for wallet in config.get("accounts", []):
        aggregated_actions = []
        num_actions = []
        for endpoint in endpoints:
            print(f"[Searching] Starting {wallet} using endpoint {endpoint}")
            scans = 0
            retries = 0
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
                    "filter": config.get("contract", "eosio.token:transfer"),
                }
                actions_call = requests.get(
                    f"{endpoint}/v2/history/get_actions", params=params
                )
                try:
                    new = json.loads(actions_call.content)
                    new["actions"]
                except:
                    if retries >= config["max-retries"]:
                        print(
                            f"[Error] Maximum retries reached on endpoint: {endpoint}."
                        )
                        exit(1)
                    # print(actions_call.content)
                    # print(actions_call.url)
                    retries += 1
                    print(
                        f"[Error] Error downloading data: {wallet}, trying again ({retries}/{config['max-retries']})"
                    )
                    time.sleep(5)
                    continue
                actions.extend(new["actions"])
                if len(new["actions"]) < params["limit"]:
                    break
                start = new["actions"][-1]["timestamp"]
                print(f"[Searching] {endpoint}: Moving to {start}")
                # delay to respect variable ratelimits between endpoints
                time.sleep(5)
                continue
            filtered = []
            # remove duplicate actions
            for action in actions:
                if action not in filtered:
                    filtered.append(action)
            if len(filtered) != 0:
                print(
                    f"[Searching] {endpoint}: {len(filtered)} actions found, ending at {filtered[-1]['timestamp']}"
                )
                aggregated_actions.extend(filtered)
                num_actions.append(len(filtered))
            else:
                print(
                    f"[Searching] {endpoint}: No actions found between {START_DATE} and {END_DATE}"
                )
                num_actions.append(0)
        if mode == "full":
            stable = True
            for i in range(1, len(num_actions)):
                if num_actions[i - 1] != num_actions[i]:
                    stable = False
            if not stable:
                print(
                    f"[Searching] Variable number of actions found for account {wallet}"
                )
                print(
                    f'[Searching] If only 1 out of 3 endpoints is showing 0, try adding its name to the "excluded-endpoints" list in the config.yaml file.'
                )
                for i in range(len(endpoints)):
                    print("[Searching]\t" + f"{endpoints[i]}: {num_actions[i]}")
                print("[Searching] Creating collated action_list")
        aggregated_action_filter = {
            f"{a['trx_id']}_{a['action_ordinal']}": a
            for a in sorted(aggregated_actions, key=lambda x: x["timestamp"])
        }
        wallet_actions[wallet] = [
            aggregated_action_filter[trx] for trx in aggregated_action_filter
        ]
        print(f"[Searching] Done {wallet}")
        print()
    print(
        "[Processing] Action record fetch from blockchain complete. Processing and exporting records now (if applicable)."
    )

    headers = [
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
        "ordinal",
        "data",
    ]
    if country:
        
        # create a cycle to loop through endpoints to minimise spam
        endpoint_cycle = cycle(endpoints)
        marketplaces = config.get(
            "marketplaces", ["neftyblocksd", "atomicdropsx"]
        )
        marketplace_prefixes = config.get(
            "marketplace-prefixes", ["NB Drop Payout - ID", "AtomicDrops sale, drop id:"]
        )
    # Create CSV files from data
    for wallet in config.get("accounts", []):
        export_path = Path(config["export-folder"]) / (
            wallet.replace(".", "_") + ".csv"
        )
        if country:
            print(
                f"[Processing] Now getting country code information for drop payouts to {wallet}. Hold tight - this will take a while."
            )
            headers.append("country_code")

        with open(export_path, "w+", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            if wallet_actions[wallet] is not None:
                for action in wallet_actions[wallet]:
                    row = []
                    row.append(str(action["timestamp"]))
                    row.append(str(action["block_num"]))
                    row.append(
                        str(action["act"]["account"])
                        + " - "
                        + str(action["act"]["name"])
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
                    row.append(str(action["action_ordinal"]))
                    row.append(json.dumps(data))
                    if country:
                        if data["from"] in marketplaces and any(data['memo'].startswith(p) for p in marketplace_prefixes):
                            try:
                                row.append(
                                    check_country_code(
                                        action["block_num"],
                                        action["trx_id"],
                                        next(endpoint_cycle),
                                    )
                                )
                            except:
                                try:
                                    row.append(
                                        check_country_code(
                                            action["block_num"],
                                            action["trx_id"],
                                            next(endpoint_cycle),
                                        )
                                    )
                                except:
                                    row.append(
                                        "Error"
                                    )
                        else:
                            row.append("")
                        if mode == "fast":
                            # delay for API limits
                            time.sleep(0.1)
                    writer.writerow(row)
                print(f"[Processing] Finished processing and exporting {wallet}!")
            else:
                print(f"[Processing] No records to export found for {wallet}!")

    print()
    print(
        f"[WAXtax] WAXTax is finished. Your files are available in the folder: {config['export-folder']}"
    )


if __name__ == "__main__":
    waxtax()

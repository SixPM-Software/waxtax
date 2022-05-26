# WAXtax

Python script to download WAX transactions

WAXtax uses the CoinGecko API and the WAX Blockchain History API to download csvs for each account you specify. Depending on the number of transactions you have, this could a significant amount of time to run.

[Windows Tutorial](https://gist.github.com/stuckatsixpm/3c79ed98d0bce808c727e0c254b0be85)  
*MacOS tutorial pending*  

## Disclaimer:

WAXtax is a tool for aggregating data from across the WAX Blockchain. It relies on the accuracy of various WAX API endpoints to provide this data.
Neither SixPM Software or the contributors to this repository are responsible for the accuracy of the data obtained from these API endpoints, nor can we confirm the accuracy of the data obtained from the aforementioned sources.

## Installation:

* Requires Python 3.8 or higher (although should theoretically run in Python 3.7, but I haven't tested this yet)
* This project uses Poetry for package management, so you can use Poetry to install all dependencies.

**Installing Poetry**

In a terminal/command prompt/powershell/etc window:
```
pip install --user poetry
```

**Installing Dependencies**

Inside the WAXTax directory, run
```
poetry install --no-dev
```
(`--no-dev` leaves out the development dependencies.)

## Usage:

**Setting up configuration**  

Edit the configuration file to suit your wallets/date range. See `config.yaml` as an example.  
`mode` - whether to run in full or fast mode. full by default. 
`max-retries` - how many times to retry a request after receiving a error from an endpoint.
`accounts` - list of accounts to check  
`contract` - token contract, only supports `eosio.token:transfer` (WAX Transfers) at the moment  
`date-range` - dates in ISO format and UTC+00 timezone, "YYYY-MM-DDTHH:MM:SS" <- Note the quotation marks  
`currency` - Currency code to convert WAX price to. See the list of supported codes [here](docs/supported_currencies.md)  
`export-folder` - Name of folder to store exported transactions in  

`full` vs `fast`:

* `full` mode will use three endpoints as a reference to give you the best chance at capturing as many actions as possible.
* `fast` mode is fast, but uses a single endpoint

**Downloading Transactions**

Inside the WAXtax directory, run
```
poetry run python waxtax
```

alternatively, try:

```
python -m poetry run python waxtax
```

## Help/Problems

If you encounter any problems, open an issue or ask for help in the [SixPM Software Discord](https://discord.gg.sixpm)

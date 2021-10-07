# WAXtax
Python script to download WAX transactions

WAXtax uses the CoinGecko API and the WAX Blockchain History API to download csvs for each account you specify. Depending on the number of transactions you have, this could a significant amount of time to run.


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
`accounts` - list of accounts to check  
`contract` - token contract, only supports `eosio.token:transfer` (WAX Transfers) at the moment  
`date-range` - dates in ISO format, "YYYY-MM-DDTHH:MM:SS" <- Note the quotation marks  
`currency` - Currency code to convert WAX price to. See the list of supported codes [here](docs/supported_currencies.md)  
`export-folder` - Name of folder to store exported transactions in  
`endpoints` - API endpoints to try to get transactions from. **Caution!** Different endpoints may produce different results, based on how up-to-date the API is.  

**Downloading Transactions**

Inside the WAXtax directory, run
```
poetry run waxtax
```

## Help/Problems

If you encounter any problems, open an issue or ask for help in the [SixPM Software Discord](https://discord.gg.sixpm)

import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'yfinance',  # Package required for fetching financial data
    'pandas'     # Package required for data manipulation
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, Dict, Any
import yfinance as yf
import pandas as pd

TickerSymbol = Annotated[str, "The ticker symbol of the financial instrument to fetch data for."]
Period = Annotated[str, "The period for which to fetch the data (e.g., '1d', '5d', '1mo', '1y')."]
Interval = Annotated[str, "The interval at which to fetch the data (e.g., '1m', '5m', '1h', '1d')."]

def fetch_financial_data(
    ticker: TickerSymbol,
    period: Period = '1mo',
    interval: Interval = '1d'
) -> Dict[str, Any]:
    """
    Fetch financial data for a given ticker symbol using the YFinance API.

    Args:
        ticker (TickerSymbol): The ticker symbol of the financial instrument.
        period (Period): The period for which to fetch the data (default is '1mo').
        interval (Interval): The interval at which to fetch the data (default is '1d').

    Returns:
        Dict[str, Any]: A dictionary containing the fetched financial data.
    """
    # Fetch the data using yfinance with auto_adjust set to False
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=False)
    
    # Convert the data to a dictionary
    data_dict = data.to_dict(orient='index')
    
    return data_dict

# Example call to the fetch_financial_data function
financial_data = fetch_financial_data(
    ticker="AAPL",
    period="1mo",
    interval="1d"
)
print(financial_data)
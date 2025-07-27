from typing import Annotated, Dict, Any
from alpha_vantage.timeseries import TimeSeries

API_KEY = 'GP0TBLU275HJI3AZ'

Symbol = Annotated[str, "The stock symbol to retrieve data for."]
Interval = Annotated[str, "The interval between data points in the time series."]

def get_intraday_data(
    symbol: Symbol,
    interval: Interval,
    api_key: Annotated[
        str,
        "The API key for authenticating with the Alpha Vantage API."
    ] = API_KEY
) -> Dict[str, Any]:
    """
    Retrieve intraday data for a given stock symbol using the Alpha Vantage API.

    Args:
        symbol (Symbol): The stock symbol to retrieve data for.
        interval (Interval): The interval between data points in the time series.
        api_key (str): The API key for the Alpha Vantage API.

    Returns:
        Dict[str, Any]: A dictionary containing the intraday data and metadata.
    """
    ts = TimeSeries(key=api_key)
    data, meta_data = ts.get_intraday(symbol=symbol, interval=interval)
    return {
        "data": data,
        "meta_data": meta_data
    }

# Example call to the get_intraday_data function
intraday_data = get_intraday_data(
    symbol="TSLA", #IBM
    interval="5min",
    api_key='GP0TBLU275HJI3AZ'
)
print(intraday_data)
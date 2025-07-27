import requests

def get_time_series_daily(symbol, apikey):
    base_url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': symbol,
        'apikey': apikey,
        'outputsize': 'full',  # Use 'compact' for latest 100 data points
        'datatype': 'json'
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        return None

# Replace with your own API key
apikey = '00000'

symbol = 'IBM'  # Specify the equity symbol
data = get_time_series_daily(symbol, apikey)
print(data)
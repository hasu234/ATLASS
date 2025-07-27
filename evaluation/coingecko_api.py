import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'pycoingecko',  # CoinGecko API client for Python
    'typing_extensions'
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from pycoingecko import CoinGeckoAPI
from typing import Annotated, Dict, List

# Initialize the CoinGecko API client
cg = CoinGeckoAPI()

CryptoPrice = Annotated[
    Dict[str, Dict[str, float]],
    "A dictionary containing the cryptocurrency IDs and their prices in specified currencies."
]

def get_crypto_price(
    crypto_ids: Annotated[
        List[str],
        "A list of cryptocurrency IDs to retrieve prices for."
    ],
    vs_currencies: Annotated[
        List[str],
        "A list of currency symbols to compare against (e.g., 'usd', 'eur')."
    ]
) -> CryptoPrice:
    """
    Retrieve the current price of specified cryptocurrencies in given currencies.

    Args:
        crypto_ids (List[str]): A list of cryptocurrency IDs.
        vs_currencies (List[str]): A list of currency symbols to compare against.

    Returns:
        CryptoPrice: A dictionary containing the cryptocurrency IDs and their prices in specified currencies.
    """
    # Convert lists to comma-separated strings
    ids = ','.join(crypto_ids)
    currencies = ','.join(vs_currencies)

    # Fetch the price data from CoinGecko
    price_data = cg.get_price(ids=ids, vs_currencies=currencies)

    return price_data

# Example call to the get_crypto_price function
crypto_prices = get_crypto_price(
    crypto_ids=['bitcoin', 'ethereum', 'litecoin'],
    vs_currencies=['usd', 'eur']
)
print(crypto_prices)

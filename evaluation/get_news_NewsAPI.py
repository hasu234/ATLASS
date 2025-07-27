import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'newsapi-python',  # The package required to interact with News API
    'typing_extensions'
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, List, Dict, Union
from newsapi import NewsApiClient

# Define the API key
API_KEY = 'f9a14697e9594873a43ab61744ba2e2c'  # Replace with your actual API key

# Define the input and output types
NewsQuery = Annotated[str, "The search query string to retrieve news articles."]
NewsResult = Annotated[
    Dict[str, Union[str, List[Dict[str, str]]]],
    "A dictionary containing the status and articles of the top news results."
]

def get_top_headlines(
    query: NewsQuery,
    api_key: Annotated[
        str,
        "The API key for authenticating with the News API."
    ],
    sources: Annotated[
        str,
        "Comma-separated string of identifiers for the news sources or blogs you want headlines from."
    ] = '',
    language: Annotated[
        str,
        "The 2-letter ISO-639-1 code of the language you want to get headlines for."
    ] = 'en',
    page_size: Annotated[
        int,
        "The number of results to return per page."
    ] = 20
) -> NewsResult:
    """
    Retrieve top headlines using the News API.

    Args:
        query (NewsQuery): The search query string.
        api_key (str): The API key for the News API.
        sources (str): The news sources to get headlines from.
        language (str): The language of the news articles.
        page_size (int): The number of results to return per page.

    Returns:
        NewsResult: A dictionary containing the status and articles of the top news results.
    """
    # Initialize the News API client
    newsapi = NewsApiClient(api_key=api_key)

    # Fetch the top headlines
    top_headlines = newsapi.get_top_headlines(q=query, sources=sources, language=language, page_size=page_size)

    return {
        "status": top_headlines.get("status"),
        "articles": top_headlines.get("articles")
    }

# Example call to the get_top_headlines function
news_results = get_top_headlines(
    query="",
    api_key=API_KEY,
    sources="bbc-news,the-verge",
    language="en",
    page_size=5
)
print(news_results)

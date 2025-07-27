import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'tavily-python',  # The package required for Tavily API
    'typing_extensions'
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, Dict, Union
from tavily import TavilyClient, InvalidAPIKeyError, MissingAPIKeyError

SearchQuery = Annotated[str, "The search query string to retrieve results from Tavily AI."]

SearchResult = Annotated[
    Dict[str, Union[str, None]],
    "A dictionary containing the query and the answer to the query."
]

def search_tavily(
    query: SearchQuery,
    api_key: Annotated[
        str,
        "The API key for authenticating with the Tavily API."
    ]
) -> SearchResult:
    """
    Perform a search using the Tavily API.

    Args:
        query (SearchQuery): The search query string.
        api_key (str): The API key for the Tavily API.

    Returns:
        SearchResult: A dictionary containing the query and the answer to the query.
    """
    try:
        tavily_client = TavilyClient(api_key=api_key)
        response = tavily_client.search(query)
        return {
            "query": query,
            "answer": response.get("results")
        }
    except InvalidAPIKeyError:
        return {"query": query, "answer": "Invalid API key provided. Please check your API key."}
    except MissingAPIKeyError:
        return {"query": query, "answer": "API key is missing. Please provide a valid API key."}

# Example call to the search_tavily function
search_results = search_tavily(
    query="Who is the current president of Bangladesh?",
    api_key="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"
)
print(search_results)
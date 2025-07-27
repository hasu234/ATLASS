import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'azure-cognitiveservices-search-websearch', # Required package for Bing Search API
    'msrest'
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, List, Dict, Union
from azure.cognitiveservices.search.websearch import WebSearchClient
from msrest.authentication import CognitiveServicesCredentials

SearchQuery = Annotated[str, "The search query string to retrieve results from the internet."]

SearchResult = Annotated[
    Dict[str, Union[str, List[Dict[str, str]]]],
    "A dictionary containing the name, URL, and snippet of the top search results."
]

def search_bing(
    query: SearchQuery,
    api_key: Annotated[
        str,
        "The API key for authenticating with the Bing Search API."
    ],
    num_results: Annotated[
        int,
        "The maximum number of search results to return."
    ] = 5
) -> SearchResult:
    """
    Perform a web search using the Bing Search API.

    Args:
        query (SearchQuery): The search query string.
        api_key (str): The API key for the Bing Search API.
        num_results (int): The number of results to fetch (default is 5).

    Returns:
        SearchResult: A dictionary containing the name, URL, and snippet of the top search results.
    """
    credentials = CognitiveServicesCredentials(api_key)
    client = WebSearchClient(endpoint="https://api.bing.microsoft.com/v7.0", credentials=credentials)
    web_data = client.web.search(query=query)

    # Parse the top search results
    results = []
    if web_data.web_pages.value:
        for result in web_data.web_pages.value[:num_results]:
            results.append({
                "name": result.name,
                "url": result.url,
                "snippet": result.snippet
            })

    return {
        "query": query,
        "results": results
    }

# Example call to the search_bing function
search_results = search_bing(
    query="What is the speed of light?",
    api_key="58882a5a75717e36e5bd72a44e94e6a64ae8b85f7d348e38dba520c7c73381ab", # Replace with the provided API_KEY
    num_results=3
)


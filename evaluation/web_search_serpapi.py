import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'google-search-results',  # Correct package name for using the SERP API
    'typing_extensions'
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, List, Dict, Union

from serpapi import GoogleSearch

SearchQuery = Annotated[str, "The search query string to retrieve results from the internet."]

SearchResult = Annotated[
    Dict[str, Union[str, List[Dict[str, str]]]],
    "A dictionary containing the title, URL, and snippets of the top search results."
]

def web_search_tool(
    query: SearchQuery,
    api_key: Annotated[
        str,
        "The API key for authenticating with the SERP API."
    ],
    num_results: Annotated[
        int,
        "The maximum number of search results to return."
    ] = 5
) -> SearchResult:
    """
    Perform a web search using the SERP API.

    Args:
        query (SearchQuery): The search query string.
        api_key (str): The API key for the SERP API.
        num_results (int): The number of results to fetch (default is 5).

    Returns:
        SearchResult: A dictionary containing the title, URL, and snippets of the top search results.
    """
    search = GoogleSearch({
        "q": query,
        "api_key": api_key
    })
    result = search.get_dict()

    # Parse the top search results
    results = []
    for result in result.get("organic_results", [])[:num_results]:
        results.append({
            "title": result.get("title"),
            "link": result.get("link"),
            "snippet": result.get("snippet")
        })

    return {
        "query": query,
        "results": results
    }

# Example call to the web_search_tool function
search_results = web_search_tool(
    query="What is the speed of light?",
    api_key="58882a5a75717e36e5bd72a44e94e6a64ae8b85f7d348e38dba520c7c73381ab",  # Replace with the provided API_KEY
    num_results=3
)
print(search_results)

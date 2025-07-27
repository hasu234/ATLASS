import requests
from bs4 import BeautifulSoup
import time
import re
import os
import json
import random
import logging
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

load_dotenv()
llm_model = os.getenv("LLM_MODEL")

# Make sure we have the required dependencies
try:
    import lxml
except ImportError:
    logging.warning("lxml parser not found, using built-in html.parser")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
BASE_TIMEOUT = 20
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
]

def find_api_documentation(api_name):
    """Search for API documentation and return relevant URLs using a fallback approach.
    
    Args:
        api_name (str): Name of the API service provider
        
    Returns:
        list: Up to 3 relevant documentation URLs
    """
    # Normalize API name for URL construction
    normalized_api = api_name.lower().replace(" ", "").replace("_", "-")
    
    # Construct common documentation URL patterns
    common_doc_sites = [
        f"https://www.{normalized_api}.com/docs",
        f"https://www.{normalized_api}.com/documentation",
        f"https://{normalized_api}.com/documentation",
        f"https://www.{normalized_api}.co/documentation",
        f"https://docs.{normalized_api}.com",
        f"https://developer.{normalized_api}.com",
        f"https://api.{normalized_api}.com/documentation",
        f"https://www.{normalized_api}.org/docs",
        f"https://www.{normalized_api}.io/docs",
        f"https://docs.{normalized_api}.io",
        f"https://dev.{normalized_api}.com",
        f"https://developers.{normalized_api}.com",
        f"https://{normalized_api}.dev",
        f"https://{normalized_api}.com/api",
        f"https://{normalized_api}.readthedocs.io",
        f"https://pypi.org/project/{normalized_api}",
        f"https://pypi.org/project/python-{normalized_api}",
        f"https://github.com/search?q={normalized_api}+api+python",
        f"https://rapidapi.com/search/{normalized_api}"
    ]
    
    # Add common variations (with dots, underscores, etc.)
    variation_with_dot = normalized_api.replace("-", ".")
    variation_with_underscore = normalized_api.replace("-", "_")
    
    # Add these variations to our URL list
    common_doc_sites.extend([
        f"https://www.{variation_with_dot}.com/docs",
        f"https://pypi.org/project/{variation_with_underscore}",
    ])
    
    # Check which URLs actually exist
    logger.info(f"Checking potential documentation URLs for {api_name}...")
    
    def check_url(url):
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            # Just do a HEAD request to check if URL exists
            response = requests.head(url, headers=headers, timeout=BASE_TIMEOUT, allow_redirects=True)
            
            # Also try GET if HEAD fails (some servers don't support HEAD)
            if response.status_code not in [200, 301, 302]:
                response = requests.get(url, headers=headers, timeout=BASE_TIMEOUT, allow_redirects=True, stream=True)
                # Close connection immediately after checking status
                response.close()
                
            if response.status_code in [200, 301, 302]:
                parsed_url = urlparse(response.url)
                # Only return URLs that point to actual domains (not search results)
                if parsed_url.netloc:
                    if any(search_site in parsed_url.netloc for search_site in ["google", "bing", "duckduckgo", "yahoo"]):
                        return None
                    logger.info(f"Found valid URL: {response.url}")
                    return response.url
        except requests.exceptions.RequestException as e:
            logger.debug(f"URL check failed for {url}: {e}")
        return None
    
    # Check URLs in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(check_url, common_doc_sites))
    
    # Filter out None results
    urls = [url for url in results if url]
    
    # Sort URLs by relevance - prioritize official docs over third-party sites
    def url_priority_score(url):
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Higher score means higher priority
        score = 0
        
        # Prioritize domains containing the API name
        if normalized_api in domain:
            score += 100
            
        # Prioritize official-looking documentation paths
        if "/docs" in url or "/documentation" in url or "/api" in url:
            score += 50
            
        # Deprioritize search results and repositories
        if "github.com/search" in url:
            score -= 30
        if "pypi.org" in url:
            score -= 10
        if "rapidapi.com" in url:
            score -= 20
            
        return score
    
    # Sort URLs by priority score (descending)
    urls.sort(key=url_priority_score, reverse=True)
    
    if not urls:
        logger.warning(f"No documentation found for {api_name}. Please check the API name.")
        return []
    
    logger.info(f"Found {len(urls)} documentation URLs for {api_name}")
    return urls[:3]

def scrape_documentation(urls):
    """Scrape and extract content from API documentation URLs with improved error handling."""
    all_content = []
    
    for url in urls:
        content = scrape_single_url(url)
        if content:
            all_content.append(content)
    
    return all_content

def scrape_single_url(url, retry_count=0):
    """Scrape a single URL with retry mechanism."""
    if retry_count >= MAX_RETRIES:
        logger.error(f"Maximum retries reached for {url}")
        return None
    
    try:
        # Add delay with jitter to avoid rate limiting
        delay = 2 + random.random() * 2
        time.sleep(delay)
        
        # Get a random user agent
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Increasing timeout and adding backoff with retry
        timeout = BASE_TIMEOUT * (retry_count + 1)
        logger.info(f"Scraping {url} (attempt {retry_count+1}/{MAX_RETRIES}, timeout: {timeout}s)")
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Use lxml parser if available, otherwise fall back to built-in parser
        try:
            soup = BeautifulSoup(response.text, 'lxml')
        except:
            # Fall back to the built-in parser
            soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract main content (this will vary based on site structure)
        # Try multiple selectors that might contain the main documentation
        content_elements = []
        
        # Check for common documentation containers
        for selector in [
            'main', 'article', 
            'div.content', 'div.documentation', 'div.docs', 
            'div.markdown-body', 'div.readme', 
            '#readme', '#documentation', '#content',
            '.api-documentation', '.api-reference'
        ]:
            elements = soup.select(selector)
            if elements:
                content_elements.extend(elements)
        
        # If we found specific content containers, use them
        if content_elements:
            combined_text = "\n".join([elem.get_text(separator='\n') for elem in content_elements])
            return {
                "url": url,
                "content": combined_text,
                "html": "".join([str(elem) for elem in content_elements])
            }
        
        # Fallback to sections with code examples
        code_blocks = soup.find_all(['pre', 'code'])
        if code_blocks:
            code_sections = []
            for block in code_blocks:
                # Get the parent container to capture context around the code
                parent = block.parent
                if parent and parent.name != 'body':
                    section_text = parent.get_text(separator='\n')
                    if 'python' in section_text.lower() or 'import' in section_text.lower():
                        code_sections.append(section_text)
            
            if code_sections:
                return {
                    "url": url,
                    "content": "\n\n".join(code_sections),
                    "html": "".join([str(block) for block in code_blocks])
                }
        
        # Second fallback to body if can't find main content area
        body = soup.body
        if body:
            return {
                "url": url,
                "content": body.get_text(separator='\n'),
                "html": str(body)
            }
        
        logger.warning(f"Could not extract content from {url}: No body found")
        return None
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout for {url}, retrying...")
        return scrape_single_url(url, retry_count + 1)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        # Only retry on connection errors, not on 4xx/5xx status codes
        if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError)):
            logger.info(f"Connection error, retrying...")
            return scrape_single_url(url, retry_count + 1)
        return None
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None

def process_documentation_with_llm(api_name, documentation_content, user_query):
    """Use LLM to understand documentation and generate functional code snippet only.
    
    Args:
        api_name (str): Name of the API service provider
        documentation_content (str): API documentation content
        user_query (str, optional): The original user query to provide context
        
    Returns:
        str: A functional Python code snippet without explanations
    """
    
    context = f"Original query: {user_query}" if user_query else ""
    
    prompt = f"""
    You are a Python developer who generates functional code examples. Your task is to create production-ready Python code for the {api_name} API that accomplishes the user's goal.

    {context}
    
    From the following API documentation, extract if code is presented in the documentation or generate COMPLETE, WORKING Python code that:
    1. Imports necessary packages
    2. Authenticates with the API (using placeholder values for keys/tokens)
    3. Makes appropriate API calls to solve the user's request
    4. Properly handles the API response
    5. Includes minimal error handling
    
    IMPORTANT INSTRUCTIONS:
    - Output ONLY executable Python code with NO explanations or text outside of code
    - Use Python comments within the code for any necessary explanations
    - Do not use markdown code blocks - just provide the raw Python code
    - The code should be complete enough to run with just API credentials
    - USE placeholder values like "YOUR_API_KEY" for credentials
    
    Documentation excerpt:
    {documentation_content[:10000]}

    You can ONLY output python code block scraped from documentation or generated from the knowledge of user query and documentation. DO NOT output any other response.
    """
    
    url = "http://10.10.10.104:11434/api/generate"
    
    try:
        payload = json.dumps({
            "model": llm_model,
            "prompt": prompt,
            "stream": False
        })
        headers = {'Content-Type': 'application/json'}
        logger.info("Sending request to LLM API...")
        response = requests.post(url, data=payload, headers=headers, timeout=180)  # Extended timeout for LLM
        
        if response.status_code != 200:
            logger.error(f"LLM API returned status code {response.status_code}: {response.text}")
            return f"Error generating code: API returned status code {response.status_code}"
        
        response_data = response.json()
        generated_content = response_data.get("response", "")
        
        if not generated_content:
            logger.error(f"LLM API returned unexpected response format: {response_data}")
            return "Error generating code: Unexpected API response format"
        
        # Extract only the Python code, removing any markdown code blocks or explanations
        code_only = extract_clean_python_code(generated_content)
        
        if not code_only:
            logger.warning("No valid Python code found in the response")
            return "no code found"  # Fallback to returning the full response
            
        return code_only
    except requests.exceptions.Timeout:
        logger.error("LLM API request timed out")
        return "Error generating code: LLM API request timed out"
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request error: {e}")
        return f"Error generating code: LLM API request error - {e}"
    except Exception as e:
        logger.error(f"Error in LLM processing: {e}")
        return f"Error generating code: {e}"


def extract_clean_python_code(content):
    """Extract clean Python code from LLM response, removing markdown and explanations.
    
    Args:
        content (str): Raw LLM-generated content
        
    Returns:
        str: Clean Python code only
    """
    # First try to extract code from markdown code blocks
    code_block_pattern = r"```(?:python)?(.*?)```"
    code_blocks = re.findall(code_block_pattern, content, re.DOTALL)
    
    if code_blocks:
        # Join all code blocks and strip leading/trailing whitespace
        return "\n\n".join(block.strip() for block in code_blocks)
    
    # If no code blocks found, try to identify Python code without markdown
    # This is trickier but we can look for common Python patterns
    lines = content.split('\n')
    code_lines = []
    in_code_section = False
    
    # Look for Python patterns like imports, function defs, variable assignments
    python_patterns = [
        r"^import\s+\w+",
        r"^from\s+\w+\s+import",
        r"^def\s+\w+\s*\(",
        r"^class\s+\w+",
        r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=",
        r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]:",
        r"^\s*try:",
        r"^\s*except",
        r"^\s*with\s+",
        r"^\s*for\s+\w+\s+in\s+",
        r"^\s*while\s+",
        r"^\s*return\s+",
        r"^\s*#.*",  # Comments
    ]
    
    # Convert patterns to a single regex for efficiency
    combined_pattern = re.compile('|'.join(python_patterns))
    
    for line in lines:
        # If line looks like Python code
        if combined_pattern.search(line) or in_code_section:
            in_code_section = True
            code_lines.append(line)
        elif line.strip() == "" and in_code_section:
            # Keep blank lines within code sections
            code_lines.append(line)
        elif code_lines and line.strip() == "":
            # Add separator blank line
            code_lines.append(line)
        else:
            # Reset if we encounter non-code content after code section
            in_code_section = False
    
    # If we found Python code, return it
    if code_lines:
        return "\n".join(code_lines)
    
    # No code found, return None
    return None

def identify_api_provider(user_query):
    """
    Analyzes a user query and identifies the most suitable API service provider.
    
    Args:
        user_query (str): The user's natural language query
        
    Returns:
        str: Name of the most appropriate API service provider
    """
    url = "http://10.10.10.104:11434/api/generate"
    
    # First check if the user explicitly mentioned a service provider
    prompt = f"""
    Analyze this user query: "{user_query}"
    
    Your task is to return ONLY a single API service provider name, with no additional text.
    
    Rules:
    1. If a specific API is mentioned in the query, extract just that name
    2. If no API is mentioned, determine the most appropriate service
    3. Return ONLY the lowercase name, nothing else - no explanations, no quotation marks
    4. Do not include words like 'API', 'service', or 'provider' in your answer
    
    Examples:
    - Query: "Get stock data for Apple using Alpha Vantage API"
    - Response: alphavantage
    
    - Query: "Find tweets about climate change"
    - Response: twitter
    
    - Query: "What's the weather in New York?"
    - Response: openweathermap
    
    Now analyze this query and respond with ONLY the service name: "{user_query}"
    """
    
    try:
        payload = json.dumps({
            "model": llm_model,
            "prompt": prompt,
            "stream": False
        })
        headers = {'Content-Type': 'application/json'}
        logger.info("Sending request to identify API provider...")
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"LLM API returned status code {response.status_code}: {response.text}")
            return "generic_api"
        
        response_data = response.json()
        provider_name = response_data.get("response", "").strip()
        print("Provider name Response: ", provider_name)
        
        # Clean up response aggressively
        provider_name = provider_name.strip('"\'.,: \n')
        provider_name = re.sub(r'^(the\s+|using\s+|with\s+|from\s+)', '', provider_name, flags=re.IGNORECASE)
        
        # Strip common suffixes
        provider_name = re.sub(r'\b(api|service|services|data|provider)$', '', provider_name, flags=re.IGNORECASE).strip()
        
        # Remove any remaining text after the first line
        if '\n' in provider_name:
            provider_name = provider_name.split('\n')[0].strip()
            
        # Remove any text after common punctuation that might indicate explanation
        for punct in [':', '.', ',', '-', '|']:
            if punct in provider_name:
                provider_name = provider_name.split(punct)[0].strip()
        
        # If we still have multiple words, take just the main name
        words = provider_name.split()
        if len(words) > 2:
            # Try to identify most likely api name (usually 1-2 words)
            provider_name = ' '.join(words[:2])
        
        # Final cleaning - remove any api/service suffix
        provider_name = re.sub(r'\s+(api|service|data)$', '', provider_name, flags=re.IGNORECASE).strip()
        
        # If empty or too long after all cleaning, return fallback
        if not provider_name or len(provider_name) > 30:
            return "generic_api"
            
        logger.info(f"Identified API provider: {provider_name}")
        return provider_name.lower()
        
    except requests.exceptions.Timeout:
        logger.error("LLM API request timed out while identifying provider")
        return "generic_api"
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request error while identifying provider: {e}")
        return "generic_api"
    except Exception as e:
        logger.error(f"Error in identifying API provider: {e}")
        return "generic_api"
        
class APICodeAgent:
    def generate_api_code(self, query):
        """Generate functional Python code for the specified API."""
        api_name = identify_api_provider(query)
        # Step 1: Find documentation
        logger.info(f"Searching for {api_name} API documentation...")
        urls = find_api_documentation(api_name)
        
        if not urls:
            return "No API documentation found. Please check the API name."
        
        # Step 2: Scrape content
        logger.info(f"Scraping documentation from {len(urls)} sources...")
        doc_content = scrape_documentation(urls)
        
        if not doc_content:
            return "Failed to extract usable content from documentation sources."
        
        # Step 3: Process with LLM
        logger.info("Analyzing documentation and generating code...")
        combined_content = "\n\n".join([f"Source: {item['url']}\n{item['content']}" for item in doc_content])
        code = process_documentation_with_llm(api_name, combined_content, query)
        return code
    
    def extract_code(self, response):
        """Extract code blocks from LLM response."""
        try:
            if "```python" in response:
                code = response.split("```python")[1].split("```")[0]
                return code.strip()
            elif "```" in response:
                code = response.split("```")[1].split("```")[0]
                return code.strip() if code.strip() else response
            else:
                return response
        except Exception as e:
            logger.error(f"Error extracting code: {e}")
            return response

# # Example usage
# if __name__ == "__main__":
#     # Initialize the agent
#     agent = APICodeAgent()
    
#     # Get code for a specific API (e.g., alphavantage)
#     # query = "Weather of Dhaka now?"
#     # query = "Last 10 days stock price of Meta using marketstack"
#     query = "What are the current top 5 trending topics on Twitter in the United States?"

    
#     api_code = agent.generate_api_code(query)
    
#     # Extract the code from the response
#     extracted_code = agent.extract_code(api_code)
    
#     # Output the result
#     print("\n--- GENERATED CODE ---\n")
#     print(extracted_code)
import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'matplotlib', 
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, Tuple, List, Union
import matplotlib

# Define a type alias for StockPriceData, specifying that it's a list of two lists: one for dates and one for prices.
StockPriceData = Annotated[Tuple[List[str], List[Union[float, int]]], "A tuple containing two lists. The first list contains the dates and the second list contains the corresponding stock prices."]

def create_line_graph(
    title: Annotated[str, "The title of the graph."],
    x_label: Annotated[str, "The label for the x-axis."],
    y_label: Annotated[str, "The label for the y-axis."],
    data: StockPriceData
) -> None:
    """
    Create a line graph representing the stock price over a given time period.

    Args:
        title (str): The title of the graph.
        x_label (str): The label for the x-axis.
        y_label (str): The label for the y-axis.
        data (StockPriceData): A tuple containing two lists. The first list contains the dates and the second list contains the corresponding stock prices.

    Returns:
        None
    """
    import matplotlib.pyplot as plt

    dates, prices = data

    plt.plot(dates, prices)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)

    # Example usage: save the plot to a file instead of displaying it.
    plt.savefig('stock_price_graph.png')

# Example call to the create_line_graph function with meaningful data.
data = (['2022-01-01', '2022-02-01', '2022-03-01'], [100, 120, 130])
create_line_graph('Stock Price Over Time', 'Date', 'Price', data)
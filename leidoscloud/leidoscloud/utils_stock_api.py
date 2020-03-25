import requests

from .models import *


def get_provider_api():
    """
    This gets the Alpha Vantage object and the objects that are providers
    :return:
    alpha: Alpha Vantage object
    provider_objects: objects that are cloud providers
    """
    alpha = API.objects.get(
        name="AlphaVantage"
    )  # because of population script, we know this exists.
    provider_objects = API.objects.filter(is_provider=True)
    return alpha, provider_objects


def get_api_key(alpha):
    """
    Gets the API key from the database
    :param alpha: object. Alpha Vantage object
    :return: key: str. API key returned
    :raise:
    ValueError
        Raised when API key cannot be found.
    """
    try:
        key = Key.objects.get(provider=alpha)
        key = key.value
    except Exception as e:
        raise ValueError("Not set! Alpha Vantage key not present. " + str(e))
    return key


def get_cloud_target(providers_api, key):
    """
    Gets the share prices for the providers from Alpha Vantage
    :param providers_api: provider objects
    :param key: Alpha Vantage API key
    :return:
    stock_dict: dictionary
        Contains the  %change of prices of each provider
    symbols: contains the symbols of the providers.
    """
    headers = {
        "Accept": "application/json",
    }
    symbols = {}
    for i in providers_api:
        symbols[i.name] = i
    stock_dict = {}
    for i in symbols.keys():
        if symbols[i].ticker_symbol is None:
            # ticker symbol does not exist! Can't check for this provider
            raise ValueError(
                "Can't compare all hosts, a stock ticker symbol for "
                + symbols[i].long_name
                + " is missing!"
            )
        response = requests.get(
            "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={}&apikey={}".format(
                symbols[i].ticker_symbol, key
            ),
            headers=headers,
            timeout=5,
        ).json()
        # Pass API errors to user instead of getting a key error
        if "Error Message" in response:
            raise RuntimeError(response["Error Message"])
        if "Global Quote" not in response:
            raise ConnectionError("Unable to retrieve stock price from Alpha Vantage")

        stock_dict[i] = float(response["Global Quote"]["10. change percent"][:-1])
    return stock_dict, symbols


def process_api_json(stock_dict, symbols):
    """
    Returns the minimum value from stocks dictionary
    :param stock_dict: Contains the %change of prices
    :param symbols: list of symbols
    :return: stock symbol of the minimum value of the stock_dict values. This is the lowest % change.
    """
    stock_min = min(stock_dict, key=lambda k: stock_dict[k])
    return symbols[stock_min]


def save_stock_data(stock_dict):
    """
    Takes the stock dictionary and saves to DB the %
    :param stock_dict:
    :return:
    """
    data = StockData.objects.create(
        google=stock_dict["google"], azure=stock_dict["azure"], aws=stock_dict["aws"]
    )
    data.save()


def save_best_prediction():
    """
    Since this is a bonus prototype feature, the implementation is a bit shoddy.
    This saves the best prediction at that specific time to the database by taking the last 72 records (24hrs).
    Then it calculates the average price over that time and the lowest average is considered best and is saved.
    :return:None
    """
    objects = StockData.objects.order_by("-time")[:72]
    google_average = 0.0
    aws_average = 0.0
    azure_average = 0.0
    for i in objects:
        google_average += i.google
        aws_average += i.aws
        azure_average += i.azure
    google_average = google_average / len(objects)
    aws_average = aws_average / len(objects)
    azure_average = azure_average / len(objects)
    if google_average < aws_average and google_average < azure_average:
        target = API.objects.get(name="google")
    elif aws_average < google_average and aws_average < azure_average:
        target = API.objects.get(name="aws")
    else:
        target = API.objects.get(name="azure")
    data = Prediction.objects.create(time=objects[0].time, provider=target)
    data.save()

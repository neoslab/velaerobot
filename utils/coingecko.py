# === Import packages ===
import requests
import time

# === Class 'CoinGecko' ===
class CoinGecko:
    """
    The CoinGecko class provides a simple mechanism to fetch and cache the current Ethereum (ETH)
    to USD exchange rate using the CoinGecko public API. The class method `ethusd` implements a
    time-to-live (TTL) strategy to avoid frequent API calls by caching the last fetched value for a
    defined duration. This is particularly useful in applications where ETH price is needed repeatedly
    and reducing API load is important.

    Parameters:
    - None (All state is maintained at the class level.)

    Returns:
    - None
    """

    # === Define 'ethprice' ===
    ethprice = None

    # === Define 'lastfetch' ===
    lastfetch = 0

    # === Define 'ttl' ===
    ttl = 60

    # === Function 'ethusd' ===
    @classmethod
    def ethusd(cls):
        """
        Fetches the current price of Ethereum (ETH) in USD using the CoinGecko API.
        This method includes internal caching with a configurable time-to-live (TTL)
        mechanism to limit the number of external API requests. If a cached value is
        recent enough, it returns that instead of querying again. API calls are retried
        only if the cache has expired or no value has been fetched yet.

        Parameters:
        - None (The method relies entirely on class-level state.)

        Returns:
        - float or None: The latest fetched ETH price in USD as a float, or None if the request fails or cannot be parsed.
        """
        now = time.time()
        if cls.ethprice is None or now - cls.lastfetch > cls.ttl:
            try:
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {"ids": "ethereum", "vs_currencies": "usd"}
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()

                print("[INFO] Scrapping Ethereum price")
                cls.ethprice = float(data["ethereum"]["usd"])
                cls.lastfetch = now
            except (requests.RequestException, ValueError, KeyError):
                pass
        return cls.ethprice

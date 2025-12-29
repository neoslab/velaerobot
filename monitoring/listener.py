# === Import libraries ===
import glob
import json
import os
import re
import time

# === Import packages ===
from bs4 import BeautifulSoup
from playwright.sync_api import Page
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from typing import Callable
from typing import Optional

# === Import dependencies ===
from utils.converter import SvgToPngConverter
from utils.models import AerodromePool
from utils.models import StoreBase
from utils.models import VelodromePool
from utils.resolver import PathResolver
from utils.scaler import NumberScaler

# === Force Playwright to use bundled Chromium ===
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PathResolver.pathabsolute("libraries/chromium")
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"


# === Class 'LiquidityScraper' ===
class LiquidityScraper:
    """
    This class handles the automated scraping, parsing, and database storage of liquidity pool data from DEX platforms
    like Velodrome and Aerodrome using Playwright for browser automation and BeautifulSoup for HTML parsing. It is
    designed for batch processing of paginated pool listings and supports dynamic progress updates via a callback.
    All parsed data is stored both in temporary JSON files and persisted into a local SQLite database via SQLAlchemy.

    Parameters:
    - None

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self):
        """
        Initializes all necessary directory paths, ensures they exist, and sets up the SQLite database connection.
        This initializer configures cache, temp, and storage directories using `PathResolver`, and prepares a SQLAlchemy
        engine with session binding to store data related to Velodrome and Aerodrome liquidity pools.

        Parameters:
        - None

        Returns:
        - None
        """
        self.rootpath = PathResolver.pathabsolute(".")
        self.cachedir = PathResolver.fullpathcache()
        self.tempdir = PathResolver.fullpathtemp()
        self.datadir = PathResolver.fullpathstorage()
        os.makedirs(self.cachedir, exist_ok=True)
        os.makedirs(self.tempdir, exist_ok=True)
        os.makedirs(self.datadir, exist_ok=True)
        self.svgconverter = SvgToPngConverter(size=32)

        # === Database Settings ===
        sqlitepath = PathResolver.pathstorage()
        self.sqlitepath = sqlitepath
        dbengine = create_engine(f"sqlite:///{sqlitepath}")
        StoreBase.metadata.create_all(dbengine)
        datasession = sessionmaker(bind=dbengine)
        self.dbsession = datasession()

    # === Function 'cleanupdirs' ===
    def cleanupdirs(self):
        """
        Cleans up cached and temporary directories by removing all HTML and JSON files respectively.
        This function is typically invoked before starting a new scraping session to avoid mixing old
        and new data, ensuring accuracy and reducing unnecessary clutter.

        Parameters:
        - None

        Returns:
        - None
        """
        for f in glob.glob(os.path.join(self.cachedir, "*.html")):
            os.remove(f)
        for f in glob.glob(os.path.join(self.tempdir, "*.json")):
            os.remove(f)

    # === Function 'extractvars' ===
    @staticmethod
    def extractvars(block):
        """
        Main orchestration function that scrapes liquidity pool data from Velodrome and Aerodrome platforms.
        The function handles directory cleanup, pool scraping using Playwright, and saves results both in JSON
        and SQLite database formats. Optional callback function allows dynamic status updates during scraping.

        Parameters:
        - updatecallback (Callable[[str, int], None], optional): A function to report scraping progress. Default is None.

        Returns:
        - None
        """
        href = block.get("href", "")
        query = href[href.find('?') + 1:]
        return dict(part.split('=') for part in query.split('&') if '=' in part)

    # === Function 'extractpairs' ===
    @staticmethod
    def extractpairs(block):
        """
        Extracts the token pair string from a given HTML block. This typically consists of two
        token names or symbols separated by a slash (e.g., "ETH/USDC"). If the element is not found,
        it returns an empty string. This method is essential for identifying the pool's trading pair.

        Parameters:
        - block (Tag): A BeautifulSoup tag object containing the liquidity pool DOM structure.

        Returns:
        - str: A cleaned string representing the token pair, or an empty string if not found.
        """
        pairs = block.select_one("div.whitespace-nowrap")
        return pairs.text.strip().replace(" / ", "/") if pairs else ""

    # === Function 'extractbasename' ===
    @staticmethod
    def extractbasename(pairs):
        """
        Extracts the base token name or symbol from a token pair string. It splits the string using
        a delimiter such as '/' or '-' and returns the first component. This helps in identifying which
        token is the 'base' asset in the pair (e.g., ETH from "ETH/USDC").

        Parameters:
        - pairs (str): Token pair string in the format "BASE/QUOTE" or "BASE-QUOTE".

        Returns:
        - str: The base token part of the pair.
        """
        for sep in ["/", "-"]:
            if sep in pairs:
                return pairs.split(sep)[0].strip()
        return pairs.strip()

    # === Function 'extractquotename' ===
    @staticmethod
    def extractquotename(pairs):
        """
        Extracts the quote token name or symbol from a token pair string. The quote token is the second
        part of the pair after the delimiter. This function supports both '/' and '-' delimiters and falls
        back to returning the input string if no delimiter is found.

        Parameters:
        - pairs (str): Token pair string formatted as "BASE/QUOTE" or "BASE-QUOTE".

        Returns:
        - str: The quote token extracted from the pair.
        """
        for sep in ["/", "-"]:
            if sep in pairs:
                return pairs.split(sep)[1].strip()
        return pairs.strip()

    # === Function 'extractnetwork' ===
    @staticmethod
    def extractnetwork(block):
        """
        Extracts the network name from the HTML block representing the liquidity pool.
        It searches for a div with specific class attributes commonly used to display
        the associated blockchain network. If no such element is found, an empty string is returned.

        Parameters:
        - block (Tag): BeautifulSoup tag containing the pool structure.

        Returns:
        - str: The network name (e.g., "Optimism", "Ethereum"), or an empty string if not available.
        """
        network = block.find("div", class_="flex items-center gap-1.5")
        return network.text.strip() if network else ""

    # === Function 'extractchainid' ===
    def extractchainid(self, block):
        """
        Extracts the numeric chain ID from the hyperlink's query parameters within the block.
        This ID is typically required to identify which blockchain the pool belongs to, such as
        1 for Ethereum Mainnet, or 10 for Optimism. The method defaults to returning 0 if the parameter is missing.

        Parameters:
        - block (Tag): BeautifulSoup tag object containing the liquidity pool DOM structure.

        Returns:
        - int: Integer representing the chain ID, or 0 if not found.
        """
        qvars = self.extractvars(block)
        return int(qvars.get("chain0", "0"))

    # === Function 'extracttype' ===
    @staticmethod
    def extracttype(block):
        """
        Extracts the type of liquidity pool (e.g., "Volatile", "Stable") from the pool's HTML block.
        It looks for a specific styled div element where the type is displayed prominently. If no
        matching element is found, an empty string is returned.

        Parameters:
        - block (Tag): A BeautifulSoup tag representing the liquidity pool block.

        Returns:
        - str: The pool type label or an empty string.
        """
        pooltype = block.find("div", class_="font-semibold text-primary")
        return pooltype.text.strip() if pooltype else ""

    # === Function 'extracttokenaddr' ===
    def extracttokenaddr(self, block, token):
        """
        Extracts the smart contract address for a given token (base or quote) from the pool block.
        It parses the query parameters in the block's href to find the token0 or token1 address.
        Returns None if the token identifier is invalid.

        Parameters:
        - block (Tag): The BeautifulSoup block representing the liquidity pool.
        - token (str): Either 'base' or 'quote' indicating which token address to extract.

        Returns:
        - str | None: The address string or None if the token type is not valid.
        """
        qvars = self.extractvars(block)
        if token == 'base':
            return qvars.get("token0", "")
        elif token == 'quote':
            return qvars.get("token1", "")
        else:
            return None

    # === Function 'extractimage' ===
    @staticmethod
    def extractimage(block, token):
        """
        Retrieves the image URL for the base or quote token logo from the pool block.
        The image tags with alt text "Token Image" are located and indexed. If not enough images
        are present or the token type is invalid, an empty string or None is returned.

        Parameters:
        - block (Tag): A BeautifulSoup tag representing the pool.
        - token (str): Either 'base' or 'quote' indicating which image URL to return.

        Returns:
        - str | None: Image URL string or None if not found or invalid input.
        """
        images = block.select('img[alt="Token Image"]')
        if token == 'base':
            return images[0]['src'] if len(images) > 0 else ''
        elif token == 'quote':
            return images[1]['src'] if len(images) > 0 else ''
        else:
            return None

    # === Function 'extractamount' ===
    @staticmethod
    def extractamount(block, token):
        """
        Parses token balances from data-test attributes in span elements in the pool block.
        Each token's balance is represented by a specific span tag. This function extracts the
        balance for either the base or quote token. If the data is incomplete or missing, None is returned.

        Parameters:
        - block (Tag): The pool's BeautifulSoup HTML block.
        - token (str): Either 'base' or 'quote'.

        Returns:
        - float | None: Token amount as float or None if not available.
        """
        tokens = block.select('span[data-test-amount]')
        amount = [float(token.get("data-test-amount")) for token in tokens if token.get("data-test-amount")]
        if token == 'base':
            return amount[0] if len(amount) > 2 else None
        elif token == 'quote':
            return amount[1] if len(amount) > 2 else None
        else:
            return None

    # === Function 'extractfees' ===
    @staticmethod
    def extractfees(block, token):
        """
        Extracts the estimated fee values associated with base or quote tokens in the pool.
        These are typically located in the same spans used for balances but at fixed positions.
        Returns None if fee information cannot be located due to insufficient spans.

        Parameters:
        - block (Tag): The BeautifulSoup tag of the pool.
        - token (str): Indicates whether to extract 'base' or 'quote' fee value.

        Returns:
        - float | None: Fee value in float or None if not found.
        """
        tokens = block.select('span[data-test-amount]')
        fees = [float(token.get("data-test-amount")) for token in tokens if token.get("data-test-amount")]
        if token == 'base':
            return fees[2] if len(fees) > 4 else None
        elif token == 'quote':
            return fees[3] if len(fees) > 4 else None
        else:
            return None

    # === Function 'extracttvl' ===
    @staticmethod
    def extracttvl(block):
        """
        Extracts the Total Value Locked (TVL) from a specific section of the HTML block.
        This value reflects the total amount of assets held in the liquidity pool and is
        a key metric for understanding pool utilization. If the field is absent or malformed,
        the function returns None.

        Parameters:
        - block (Tag): The HTML element representing the liquidity pool.

        Returns:
        - float | None: Parsed TVL value as a float, or None if extraction fails.
        """
        tvl = None
        html = block.find("div", class_="truncate xl:text-right")
        if html:
            elm = html.select_one("div.truncate.text-sm")
            if elm:
                tvl = NumberScaler.parsenumber(elm.text)
        return tvl

    # === Function 'extractvolume' ===
    @staticmethod
    def extractvolume(block):
        """
        Retrieves the recent trading volume from the pool's HTML block by locating a div
        containing a dollar-sign prefixed number. This value gives insight into how active
        the pool is. If no such field is present or parsing fails, None is returned.

        Parameters:
        - block (Tag): HTML block representing the liquidity pool.

        Returns:
        - float | None: Volume amount in USD as float or None.
        """
        elm = block.find("div", string=lambda s: s and "$" in s and "Volume" not in s)
        return NumberScaler.parsenumber(elm.text) if elm else None

    # === Function 'extractapr' ===
    @staticmethod
    def extractapr(block):
        """
        Extracts the APR (Annual Percentage Rate) shown within the liquidity pool block.
        It attempts multiple strategies including parsing data-test-amount attributes and
        matching percentage text. APR is a key metric used to estimate passive income.

        Parameters:
        - block (Tag): The BeautifulSoup tag of the pool.

        Returns:
        - float | None: The APR value as a float or None if no valid value is detected.
        """
        apr = None
        label = block.find("div", string=lambda s: s and "APR" in s)
        if label:
            container = label.find_parent("div")
            if container:
                span = container.find("span", attrs={"data-test-amount": True})
                if span:
                    try:
                        apr = float(span["data-test-amount"])
                        return apr
                    except ValueError:
                        pass

                for span in container.find_all("span"):
                    aprtxt= span.get_text(strip=True)
                    if re.match(r"\+\d[\d,]*%", aprtxt):
                        try:
                            apr = float(aprtxt.replace("+", "").replace("%", "").replace(",", ""))
                            return apr
                        except ValueError:
                            continue

        return apr

    # === Function 'extractgroup' ===
    @staticmethod
    def extractgroup(block):
        """
        Extracts an optional group score or tier percentage from the pool block.
        This value may be used to classify pools or rank them based on volume,
        liquidity, or other hidden metrics. If the value is not numeric, returns None.

        Parameters:
        - block (Tag): A BeautifulSoup object representing the liquidity pool.

        Returns:
        - float | None: The group score as a float, or None if invalid or missing.
        """
        group = block.select_one("div.whitespace-nowrap + div span")
        if group:
            try:
                return float(group.text.strip().replace('%', ''))
            except ValueError:
                return None
        return None

    # === Function 'extractfiat' ===
    @staticmethod
    def extractfiat(block):
        """
        Attempts to parse a fiat-equivalent price from the liquidity pool block.
        The fiat value typically includes a dollar sign and represents the estimated USD value
        of the total pool. If this format is not found or parsing fails, the function returns None.

        Parameters:
        - block (Tag): The DOM block representing the pool.

        Returns:
        - float | None: Fiat equivalent value of the pool or None if not found.
        """
        html = block.select_one('div.truncate.text-sm.xl\\:text-right')
        if not html:
            return None

        if html.contents:
            raw = html.contents[0].strip()
            match = re.search(r'~\$(\d[\d,]*\.?\d*)', raw)
            if match:
                clean = match.group(1).replace(",", "").replace(" ", "")
                value = float(clean)
                return value
        return None

    # === Function 'extractfactory' ===
    def extractfactory(self, block):
        """
        Extracts the factory contract identifier from the query parameters in the pool's href.
        This factory address indicates which smart contract deployed the pool, useful for auditing
        or categorizing pools by DEX implementations.

        Parameters:
        - block (Tag): The HTML block with hyperlink and metadata.

        Returns:
        - str: Factory address string or empty if missing.
        """
        qvars = self.extractvars(block)
        return qvars.get("factory", "")

    # === Function 'extractbaseprice' ===
    def extractbaseprice(self, block):
        """
        Extracts the price of the base token from the pool block. It uses the token0 address from the
        URL query parameters to find the correct span element tagged with that address. This function
        returns the corresponding token price if matched, otherwise None.

        Parameters:
        - block (Tag): The DOM element block representing the pool.

        Returns:
        - float | None: The base token price or None if unmatched or not found.
        """
        qvars = self.extractvars(block)
        for div in block.select('div[data-testid^="pool-balance-"]'):
            val = div.select_one('span[data-test-amount]')
            if val:
                addr = div['data-testid'].replace('pool-balance-', '')
                amt = val.get("data-test-amount")
                if addr.lower() == qvars.get("token0", "").lower():
                    return float(amt)
        return None

    # === Function 'extractquoteprice' ===
    def extractquoteprice(self, block):
        """
        Extracts the price of the quote token from the pool block by matching the token1 address
        against data-testid values. Similar in logic to extractbaseprice but targets the second token.
        Returns None if the quote token is not found or no value is associated.

        Parameters:
        - block (Tag): BeautifulSoup tag with all pool balance HTML.

        Returns:
        - float | None: Quote token price as float, or None if not found.
        """
        qvars = self.extractvars(block)
        for div in block.select('div[data-testid^="pool-balance-"]'):
            val = div.select_one('span[data-test-amount]')
            if val:
                addr = div['data-testid'].replace('pool-balance-', '')
                amt = val.get("data-test-amount")
                if addr.lower() == qvars.get("token1", "").lower():
                    return float(amt)
        return None

    # === Function 'extracthref' ===
    @staticmethod
    def extracthref(block):
        """
        Returns the href attribute of a given block, which typically contains
        a URL or route for navigating to a detailed view of the liquidity pool.
        Used primarily to extract identifiers or metadata from hyperlinks embedded in the DOM.

        Parameters:
        - block (Tag): A tag object expected to contain a href attribute.

        Returns:
        - str: The raw href URL string or an empty string if not found.
        """
        return block.get("href", "")

    # === Function 'parsepools' ===
    def parsepools(self, sitename, baseurl, updatecallback=None, base_index=0):
        """
        Handles browser automation and HTML content retrieval for pool listings, page by page.
        For each page of results, it loads the URL, waits for DOM readiness, saves the HTML content,
        parses the liquidity pools using BeautifulSoup, and optionally reports progress.

        Parameters:
        - sitename (str): Name of the DEX site being scraped (e.g., "velodrome" or "aerodrome").
        - baseurl (str): URL to the liquidity pools page.
        - updatecallback (Callable, optional): Function for progress reporting.
        - base_index (int): Offset index for status tracking.

        Returns:
        - list: List of dictionaries representing each parsed liquidity pool.
        """
        allpools = []
        pagelimit = 36 if sitename == "aerodrome" else 18
        maxretries = 30
        itemselector = 'a[data-testid="liquidity-pool"]'

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ))

            for pagequery in range(1, pagelimit + 1):
                index = base_index + pagequery
                servernbr = pagequery * 25
                servermax = pagelimit * 25
                success = False

                for attempt in range(1, maxretries + 1):
                    if updatecallback:
                        updatecallback(f"{sitename.capitalize()} pools {servernbr}/{servermax}", index)

                    print(f"[INFO] Extracting {sitename.capitalize()} pools {servernbr}/{servermax}")
                    url = f"{baseurl}?page={pagequery}&limit=25"
                    try:
                        page = context.new_page()
                        assert isinstance(page, Page)
                        page.set_default_timeout(20000)
                        page.goto(url, wait_until="networkidle", timeout=20000)
                        page.wait_for_selector(itemselector, timeout=10000)

                        htmlcode = page.content()
                        htmlpath = os.path.join(self.cachedir, f"{sitename}_page{pagequery}.html")
                        with open(htmlpath, "w", encoding="utf-8") as f:
                            f.write(htmlcode)

                        soup = BeautifulSoup(htmlcode, "html.parser")
                        pools = self.parsesoup(soup)

                        if not pools:
                            break

                        allpools.extend(pools)
                        success = True
                        page.close()
                        break

                    except (TimeoutError, OSError, ValueError):
                        pass

                    finally:
                        try:
                            page.close()
                        except (TimeoutError, OSError):
                            pass
                        time.sleep(2)

                if not success:
                    continue

            context.close()
            browser.close()
        return allpools

    # === Function 'parsesoup' ===
    def parsesoup(self, soup):
        """
        Parses an HTML soup containing liquidity pool blocks and extracts relevant fields.
        The function relies on the internal `extract*` helper methods to read information such
        as token symbols, fees, prices, and liquidity metrics from each block in the DOM.

        Parameters:
        - soup (BeautifulSoup): Parsed HTML document from a Velodrome or Aerodrome page.

        Returns:
        - list: A list of dictionaries, each representing one liquidity pool with parsed data fields.
        """
        pools = []
        for block in soup.select('a[data-testid="liquidity-pool"]'):
            pairs = self.extractpairs(block)
            baselogo = self.extractimage(block, 'base')
            quotelogo = self.extractimage(block, 'quote')
            basepng = self.svgconverter.convertsvg(baselogo) if baselogo else ""
            quotepng = self.svgconverter.convertsvg(quotelogo) if quotelogo else ""

            pool = {
                "pairs": pairs,
                "basename": self.extractbasename(pairs),
                "quotename": self.extractquotename(pairs),
                "network": self.extractnetwork(block),
                "chainid": self.extractchainid(block),
                "type": self.extracttype(block),
                "baseaddr": self.extracttokenaddr(block, 'base'),
                "baselogo": basepng,
                "basebalance": self.extractamount(block, 'base'),
                "basefees": self.extractfees(block, 'base'),
                "baseprice": self.extractbaseprice(block),
                "quoteaddr": self.extracttokenaddr(block, 'quote'),
                "quotelogo": quotepng,
                "quotebalance": self.extractamount(block, 'quote'),
                "quotefees": self.extractfees(block, 'quote'),
                "quoteprice": self.extractquoteprice(block),
                "tvl": self.extracttvl(block),
                "volume": self.extractvolume(block),
                "apr": self.extractapr(block),
                "group": self.extractgroup(block),
                "fiat": self.extractfiat(block),
                "factory": self.extractfactory(block),
                "url": self.extracthref(block)
            }

            pools.append(pool)
        return pools

    # === Function 'savetodb' ===
    def savetodb(self, tableclass, data):
        """
        Stores the parsed pool data into the corresponding SQLAlchemy database table.
        It clears any existing records in the table to ensure a clean import, resets auto-increment IDs,
        and inserts all new rows into the table using the provided `tableclass` definition.

        Parameters:
        - tableclass (DeclarativeMeta): SQLAlchemy ORM model class to represent the target table.
        - data (list): List of dictionaries containing pool data to be saved.

        Returns:
        - None
        """
        tablename = tableclass.__tablename__
        self.dbsession.query(tableclass).delete(synchronize_session=False)
        self.dbsession.commit()
        self.dbsession.execute(text("DELETE FROM sqlite_sequence WHERE name = :name"), {"name": tablename})
        self.dbsession.commit()

        self.dbsession.query(tableclass).delete()
        for item in data:
            row = tableclass(
                pairs=item.get("pairs"),
                basename=item.get("basename"),
                quotename=item.get("quotename"),
                network=item.get("network"),
                chainid=item.get("chainid"),
                type=item.get("type"),
                baseaddr=item.get("baseaddr"),
                baselogo=item.get("baselogo"),
                basebalance=item.get("basebalance"),
                basefees=item.get("basefees"),
                baseprice=item.get("baseprice"),
                quoteaddr=item.get("quoteaddr"),
                quotelogo=item.get("quotelogo"),
                quotebalance=item.get("quotebalance"),
                quotefees=item.get("quotefees"),
                quoteprice=item.get("quoteprice"),
                tvl=item.get("tvl"),
                volume=item.get("volume"),
                apr=item.get("apr"),
                group=item.get("group"),
                fiat=item.get("fiat"),
                factory=item.get("factory"),
                url=item.get("url"),
                sync=int(time.time())
            )

            self.dbsession.add(row)
        self.dbsession.commit()

    # === Function 'scrapeall' ===
    def scrapeall(self, updatecallback: Optional[Callable[[str, int], None]] = None):
        """
        Main orchestration function that scrapes liquidity pool data from Velodrome and Aerodrome platforms.
        The function handles directory cleanup, pool scraping using Playwright, and saves results both in JSON
        and SQLite database formats. Optional callback function allows dynamic status updates during scraping.

        Parameters:
        - updatecallback (Callable[[str, int], None], optional): A function to report scraping progress. Default is None.

        Returns:
        - None
        """
        self.cleanupdirs()
        ts = int(time.time())

        velo = self.parsepools("velodrome", "https://velodrome.finance/liquidity", updatecallback, 0)
        with open(os.path.join(self.tempdir, "velodrome.json"), "w", encoding="utf-8") as f:
            json.dump({"timestamp": ts, "pools": velo}, f, indent=2)
        print("[INFO] Saving velodrome.json")

        aero = self.parsepools("aerodrome", "https://aerodrome.finance/liquidity", updatecallback, 18)
        with open(os.path.join(self.tempdir, "aerodrome.json"), "w", encoding="utf-8") as f:
            json.dump({"timestamp": ts, "pools": aero}, f, indent=2)
        print("[INFO] Saving aerodrome.json")

        self.savetodb(VelodromePool, velo)
        self.savetodb(AerodromePool, aero)
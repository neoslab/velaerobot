# === Import libraries ===
import datetime

# === Import packages ===
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base

# === SQLAlchemy Setup ===
StoreBase = declarative_base()


# === Class 'AerodromePool' ===
class AerodromePool(StoreBase):
    """
    The AerodromePool class defines the database schema for storing real-time and historical data
    about liquidity pools specific to the Aerodrome protocol. This SQLAlchemy ORM model is used
    to persist on-chain pool information such as token balances, fees, prices, TVL, and APR
    for analytical and monitoring purposes. It also tracks metadata such as network, chain ID, and sync state.

    Parameters:
    - id (int): Auto-incremented primary key.
    - datetime (datetime): Timestamp with timezone when the record was inserted.
    - pairs (str): Combined token pair identifier.
    - basename (str): Name of the base token.
    - quotename (str): Name of the quote token.
    - network (str): Name of the blockchain network (e.g., mainnet, testnet).
    - chainid (int): Chain ID associated with the network.
    - type (str): Type of pool (e.g., stable, volatile).
    - baseaddr (str): Contract address of the base token.
    - baselogo (str): URL or path to the base token logo.
    - basebalance (float): Balance of the base token in the pool.
    - basefees (float): Fees earned in base token.
    - baseprice (float): Price of the base token.
    - quoteaddr (str): Contract address of the quote token.
    - quotelogo (str): URL or path to the quote token logo.
    - quotebalance (float): Balance of the quote token in the pool.
    - quotefees (float): Fees earned in quote token.
    - quoteprice (float): Price of the quote token.
    - tvl (float): Total value locked in the pool.
    - volume (float): 24-hour trading volume.
    - apr (float): Annual percentage rate (return) for providing liquidity.
    - group (float): Grouping tag or numerical cluster label for analytics.
    - fiat (float): Fiat equivalent value of the pool.
    - factory (str): Factory contract address or label.
    - url (str): External URL to the pool's detailed view.
    - sync (bigint): Block or sync marker for ordering updates.

    Returns:
    - None
    """

    __tablename__ = 'aeropools'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC))
    pairs = Column(String, index=True)
    basename = Column(String, index=True)
    quotename = Column(String, index=True)
    network = Column(String)
    chainid = Column(Integer)
    type = Column(String)
    baseaddr = Column(String)
    baselogo = Column(String)
    basebalance = Column(Float)
    basefees = Column(Float)
    baseprice = Column(Float)
    quoteaddr = Column(String)
    quotelogo = Column(String)
    quotebalance = Column(Float)
    quotefees = Column(Float)
    quoteprice = Column(Float)
    tvl = Column(Float)
    volume = Column(Float)
    apr = Column(Float)
    group = Column(Float)
    fiat = Column(Float)
    factory = Column(String)
    url = Column(String)
    sync = Column(BigInteger, index=True)

# === Class 'VelodromePool' ===
class VelodromePool(StoreBase):
    """
    The VelodromePool class is a SQLAlchemy model used for persisting data on pools
    in the Velodrome decentralized exchange protocol. It mirrors the structure of AerodromePool,
    enabling a unified schema across protocols. This model supports tracking detailed pool metrics
    such as token balances, price feeds, liquidity stats, and protocol-specific metadata
    for analysis, visualization, or synchronization with blockchain data.

    Parameters:
    - id (int): Auto-incremented primary key.
    - datetime (datetime): Record creation timestamp in UTC.
    - pairs (str): Token pair shorthand (e.g., "ETH/USDC").
    - basename (str): Name of the base token.
    - quotename (str): Name of the quote token.
    - network (str): Blockchain name (e.g., "Optimism").
    - chainid (int): Network chain identifier.
    - type (str): Pool type descriptor.
    - baseaddr (str): Base token contract address.
    - baselogo (str): Logo URL or path for the base token.
    - basebalance (float): Current base token amount in the pool.
    - basefees (float): Accumulated fees in base token.
    - baseprice (float): Price of base token in quote terms.
    - quoteaddr (str): Quote token contract address.
    - quotelogo (str): Logo URL or path for the quote token.
    - quotebalance (float): Current quote token amount in the pool.
    - quotefees (float): Accumulated fees in quote token.
    - quoteprice (float): Price of quote token in base terms.
    - tvl (float): Total value locked in the pool in USD or fiat.
    - volume (float): Daily trading volume.
    - apr (float): Annualized return percentage.
    - group (float): Optional grouping identifier.
    - fiat (float): Fiat value equivalent of the pool.
    - factory (str): Factory contract associated with the pool.
    - url (str): External or internal link for pool details.
    - sync (bigint): Block height or sync marker.

    Returns:
    - None
    """

    __tablename__ = 'velopools'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC))
    pairs = Column(String, index=True)
    basename = Column(String, index=True)
    quotename = Column(String, index=True)
    network = Column(String)
    chainid = Column(Integer)
    type = Column(String)
    baseaddr = Column(String)
    baselogo = Column(String)
    basebalance = Column(Float)
    basefees = Column(Float)
    baseprice = Column(Float)
    quoteaddr = Column(String)
    quotelogo = Column(String)
    quotebalance = Column(Float)
    quotefees = Column(Float)
    quoteprice = Column(Float)
    tvl = Column(Float)
    volume = Column(Float)
    apr = Column(Float)
    group = Column(Float)
    fiat = Column(Float)
    factory = Column(String)
    url = Column(String)
    sync = Column(BigInteger, index=True)


# === Class 'LiquidityLogs' ===
class LiquidityLogs(StoreBase):
    """
    The LiquidityLogs class represents historical snapshots and user-specific deposit
    records of liquidity pool activity. It is used to log every liquidity provision event
    for monitoring, analytics, or auditing. Additional fields like `stacked`, `status`,
    and new fields `priority`, `bull`, and `bear` allow users to annotate the intent and
    timing strategy for each liquidity action.

    Parameters:
    - id (int): Primary key identifier for the log entry.
    - datetime (datetime): UTC timestamp when the entry was recorded.
    - pairs (str): Token pair name (e.g., ETH/USDC).
    - basename (str): Base asset name.
    - quotename (str): Quote asset name.
    - network (str): Blockchain network (e.g., Optimism).
    - chainid (int): Chain ID of the network.
    - type (str): Pool classification (stable, volatile, etc.).
    - baseaddr (str): Address of base token.
    - baselogo (str): Base token logo path or URL.
    - basebalance (float): Balance of base token.
    - basefees (float): Fees collected in base token.
    - baseprice (float): Price of base token.
    - quoteaddr (str): Address of quote token.
    - quotelogo (str): Quote token logo path or URL.
    - quotebalance (float): Balance of quote token.
    - quotefees (float): Fees collected in quote token.
    - quoteprice (float): Price of quote token.
    - tvl (float): Total value locked in the pool (USD).
    - volume (float): 24h volume of trading.
    - apr (float): Annual percentage return (APR).
    - group (float): Analytical grouping cluster or tag.
    - fiat (float): Estimated fiat value of the deposit.
    - factory (str): Factory contract or DEX reference.
    - url (str): External link to pool info or analytics.
    - stacked (float): Amount of ETH or token staked.
    - status (bool): Boolean indicating active (True) or unstacked (False).
    - priority (str): User-assigned priority or label for the pool.
    - bull (str): User-defined timing strategy for bullish entry.
    - bear (str): User-defined timing strategy for bearish entry.

    Returns:
    - None
    """

    __tablename__ = 'liquidity'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC))
    pairs = Column(String, index=True)
    basename = Column(String, index=True)
    quotename = Column(String, index=True)
    network = Column(String)
    chainid = Column(Integer)
    type = Column(String)
    baseaddr = Column(String)
    baselogo = Column(String)
    basebalance = Column(Float)
    basefees = Column(Float)
    baseprice = Column(Float)
    quoteaddr = Column(String)
    quotelogo = Column(String)
    quotebalance = Column(Float)
    quotefees = Column(Float)
    quoteprice = Column(Float)
    tvl = Column(Float)
    volume = Column(Float)
    apr = Column(Float)
    group = Column(Float)
    fiat = Column(Float)
    factory = Column(String)
    url = Column(String)
    stacked = Column(Float)
    status = Column(Boolean)
    priority = Column(String)
    bull = Column(String)
    bear = Column(String)
# === Import libraries ===
import os
import math
import time

# === Import packages ===
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# === Import dependencies ===
from utils.models import AerodromePool
from utils.models import StoreBase
from utils.models import VelodromePool


# === Class 'SyncHandler' ===
class SyncHandler:
    """
    The SyncHandler class provides functionality to manage synchronization logic for local SQLite databases
    containing liquidity pool data. It connects to the database, verifies table existence, checks the age
    of the most recent entries, and determines whether a new sync operation is required. This class is
    useful for automated data pipelines or GUI components that trigger updates based on data staleness.

    Parameters:
    - sqlitepath (str): The full path to the SQLite database file.
    - maxseconds (int): The maximum allowed age (in seconds) for data before triggering an update.

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self, sqlitepath, maxseconds=3600):
        """
        Initializes the SyncHandler instance by setting the SQLite database path and
        the maximum data age threshold. The SQLAlchemy engine and session are initialized
        as `None` and are only instantiated when a database connection is required.

        Parameters:
        - sqlitepath (str): File path to the SQLite database.
        - maxseconds (int): Maximum allowable data age in seconds before triggering a sync.

        Returns:
        - None
        """
        self.sqlitepath = sqlitepath
        self.maxage = maxseconds
        self.engine = None
        self.session = None

    # === Function 'connect' ===
    def sqlconnect(self):
        """
        Establishes a connection to the specified SQLite database using SQLAlchemy.
        If the database file does not exist, the function returns `False`.
        Otherwise, it initializes the engine and session, binds the models,
        and ensures all tables are created if they don't already exist.

        Parameters:
        - None

        Returns:
        - bool: True if the connection is successful, False if the database file is missing.
        """
        if not os.path.exists(self.sqlitepath):
            return False

        print("[INFO] Connecting to SQLite")
        self.engine = create_engine(f"sqlite:///{self.sqlitepath}")
        StoreBase.metadata.bind = self.engine
        datasession = sessionmaker(bind=self.engine)
        self.session = datasession()
        StoreBase.metadata.create_all(self.engine)
        return True

    # === Function 'checktable' ===
    def checktable(self, tablename):
        """
        Checks whether a specific table exists in the currently connected SQLite database.
        Uses SQLAlchemy's inspector to retrieve the list of tables and determine if
        the requested one is present.

        Parameters:
        - tablename (str): The name of the table to check for existence.

        Returns:
        - bool: True if the table exists, False otherwise.
        """
        print("[INFO] Checking table")
        inspector = inspect(self.engine)
        return tablename in inspector.get_table_names()

    # === Function 'checkstatus' ===
    def checkstatus(self, model):
        """
        Determines the age of the most recent `sync` timestamp from the specified model's table.
        Returns the age in seconds if available and valid, or infinity if no valid timestamp is found.
        This is used to decide if the data is stale and needs updating.

        Parameters:
        - model (SQLAlchemy model): The ORM class representing the table to query.

        Returns:
        - float: Age of the most recent `sync` value in seconds, or float("inf") on failure.
        """
        try:
            last = self.session.query(func.max(model.sync)).scalar()
            now = int(time.time())
            age = now - last if isinstance(last, int) and last > 0 else float("inf")
            print("[INFO] Checking status")
            return age if math.isfinite(age) and age >= 0 else float("inf")
        except (SQLAlchemyError, AttributeError, TypeError, ValueError):
            print("[ERROR] Error checking status")
            return float("inf")

    # === Function 'checkupdate' ===
    def checkupdate(self):
        """
        Main method to determine whether a synchronization update is required.
        Connects to the database and checks the presence and freshness of the `aeropools`
        and `velopools` tables. If any table is missing or the latest data is older than
        the specified max age, it returns `True`. Otherwise, returns `False`.

        Parameters:
        - None

        Returns:
        - bool: True if a sync update is needed, False otherwise.
        """
        if not self.sqlconnect():
            return True

        needexec = False
        if not self.checktable("aeropools"):
            needexec = True
        else:
            age = self.checkstatus(AerodromePool)
            if not math.isfinite(age) or age > self.maxage:
                needexec = True

        if not self.checktable("velopools"):
            needexec = True
        else:
            age = self.checkstatus(VelodromePool)
            if not math.isfinite(age) or age > self.maxage:
                needexec = True

        if not needexec:
            print("[INFO] Update not needed")
        else:
            print("[INFO] Update needed")

        self.session.close()
        return needexec
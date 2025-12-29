# === Import libraries ===
import os
import sys


# === Class 'PathResolver' ===
class PathResolver:
    """
    The PathResolver class provides static utility methods for generating consistent absolute file paths
    based on the application's runtime environment. It supports both development and frozen (e.g., PyInstaller)
    modes by resolving paths accordingly. This class is essential for locating assets, temporary files, cached
    data, configuration files, and databases, regardless of the system or packaging context.

    Parameters:
    - None (All methods are static; the class is not meant to be instantiated.)

    Returns:
    - None
    """

    # === Function 'frozenbase' ===
    @staticmethod
    def frozenbase() -> str:
        """
        Returns the base path for bundled read-only assets.
        If running under PyInstaller, this uses the temporary unpacked folder.
        Otherwise, it uses the current working directory.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the asset base directory.
        """
        return getattr(sys, "_MEIPASS", os.path.abspath("."))

    # === Function 'userbasedata' ===
    @staticmethod
    def userbasedata() -> str:
        """
        Returns the base path for user-writable persistent data.
        This path varies by operating system and ensures separation from bundled files.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the user data directory.
        """
        if sys.platform == "win32":
            return os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "VelAerobot")
        elif sys.platform == "darwin":
            return os.path.join(os.path.expanduser("~/Library/Application Support"), "VelAerobot")
        else:
            return os.path.join(os.path.expanduser("~/.local/share"), "VelAerobot")

    # === Function 'pathabsolute' ===
    @staticmethod
    def pathabsolute(relativepath: str) -> str:
        """
        Resolves a relative path into an absolute path, taking into account whether the script is running
        in a frozen state (e.g., packaged with PyInstaller). If running in such a mode, it uses the temporary
        folder assigned to the executable. Otherwise, it defaults to the current working directory.

        Parameters:
        - relativepath (str): A relative path to be resolved into an absolute file system path.

        Returns:
        - str: The absolute path derived from the runtime environment and given relative path.
        """
        return os.path.join(PathResolver.frozenbase(), relativepath)

    # === Function 'pathbase' ===
    @staticmethod
    def pathbase(subfolder: str) -> str:
        """
        Returns the base path for a given subfolder. When the application is frozen, it places the folder
        inside the user's APPDATA directory (Windows) or home directory. In development mode, it does the same
        for consistency. The subfolder is created if it does not exist.

        Parameters:
        - subfolder (str): The subdirectory to be resolved and created if it doesn't exist.

        Returns:
        - str: The absolute path to the resolved base directory.
        """
        base_path = os.path.join(PathResolver.userbasedata(), subfolder)
        os.makedirs(base_path, exist_ok=True)
        return base_path

    # === Function 'fullpathicons' ===
    @staticmethod
    def fullpathicons() -> str:
        """
        Returns the absolute path to the folder where icon assets used throughout the application
        are stored. Specifically, this path targets the 'icons' directory nested under 'assets/images'.
        The method ensures the correct directory structure is generated depending on whether the
        application is running in development mode or has been frozen using a packager like PyInstaller.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the 'assets/images/icons' directory used for storing UI icon files.
        """
        return PathResolver.pathabsolute(os.path.join("assets", "images", "icons"))

    # === Function 'fullpathtemp' ===
    @staticmethod
    def fullpathtemp() -> str:
        """
        Returns the absolute path to the temporary storage directory used by the application.
        This is built upon the standard base path determined by the environment, with "temp"
        as the target subfolder. Ensures the directory exists.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the temporary storage folder.
        """
        return PathResolver.pathbase("temp")

    # === Function 'fullpathcache' ===
    @staticmethod
    def fullpathcache() -> str:
        """
        Returns the absolute path to the application's cache directory. The cache folder is
        used to store volatile or short-lived files needed during runtime. Ensures the folder exists
        within the appropriate environment-specific base path.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the cache storage folder.
        """
        return PathResolver.pathbase("cache")

    # === Function 'fullpathpng' ===
    @staticmethod
    def fullpathpng() -> str:
        """
        Returns the absolute path to the directory where PNG icon files are stored.
        Ensures the directory exists, and resolves the full path correctly depending
        on whether the app is running in a frozen or development environment.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the PNG icons folder under 'tokens/png'.
        """
        return PathResolver.pathbase(os.path.join("tokens", "png"))

    # === Function 'fullpathsvg' ===
    @staticmethod
    def fullpathsvg() -> str:
        """
        Returns the absolute path to the directory where SVG icon files are stored.
        Ensures the directory exists, and resolves the full path correctly depending
        on whether the app is running in a frozen or development environment.

        Parameters:
        - None

        Returns:
        - str: Absolute path to the SVG icons folder under 'tokens/svg'.
        """
        return PathResolver.pathbase(os.path.join("tokens", "svg"))

    # === Function 'fullpathstorage' ===
    @staticmethod
    def fullpathstorage() -> str:
        """
        Returns the absolute path to the application's primary storage directory, typically
        used for persistent database files and long-term data. The folder is located based
        on the application's operating mode (frozen or not).

        Parameters:
        - None

        Returns:
        - str: Absolute path to the storage base directory (e.g., "database").
        """
        return PathResolver.pathbase("database")

    # === Function 'pathstorage' ===
    @staticmethod
    def pathstorage() -> str:
        """
        Returns the full file path to the application's main database file, typically named "pools.db".
        This method ensures that the base directory exists and properly appends the database filename
        to the resolved storage path.

        Parameters:
        - None

        Returns:
        - str: Full path to the "pools.db" file inside the storage directory.
        """
        return os.path.join(PathResolver.pathbase("database"), "pools.db")

    # === Function 'pathconfig' ===
    @staticmethod
    def pathconfig() -> str:
        """
        Returns the full file path to the application's configuration file named "settings.json".
        This configuration file is stored under the "config" directory, which is resolved and created
        automatically depending on the environment.

        Parameters:
        - None

        Returns:
        - str: Full path to the "settings.json" configuration file.
        """
        return os.path.join(PathResolver.pathbase("config"), "settings.json")

    # === Function 'pathprotocol' ===
    @staticmethod
    def pathprotocol() -> str:
        """
        Returns the full file path to the application's protocol definition file, "protocol.json",
        which is stored in the "config" directory. The method ensures directory existence and proper
        path resolution regardless of runtime context.

        Parameters:
        - None

        Returns:
        - str: Full path to the "protocol.json" file used for defining communication or data protocols.
        """
        return os.path.join(PathResolver.pathbase("config"), "protocol.json")
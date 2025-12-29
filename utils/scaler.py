# === Class 'NumberScaler' ===
class NumberScaler:
    """
    The NumberScaler class provides static utility methods for formatting large numeric values
    into human-readable strings with suffixes like K (thousand), M (million), and B (billion),
    as well as parsing such formatted strings back into their numeric equivalents.
    This class is commonly used in financial dashboards, data visualizations, and UIs
    where compact number representation improves clarity and saves space.

    Parameters:
    - None (All methods are static and the class does not require instantiation.)

    Returns:
    - None
    """

    # === Function 'formatsuffix' ===
    @staticmethod
    def formatsuffix(value):
        """
        Converts a numeric value into a shortened string representation with a suffix
        indicating its magnitude (e.g., K for thousands, M for millions, B for billions).
        The function handles floats and integers, and defaults to 'n/a' for invalid inputs.
        Useful for displaying simplified values on dashboards or reports where space is limited.

        Parameters:
        - value (int or float or str): A numeric value or numeric string to be converted.

        Returns:
        - str: A formatted string with a magnitude suffix (e.g., "1.23K", "2.00M", "4.56B") or "n/a" if the value cannot be parsed as a number.
        """
        try:
            num = float(value)
            if num >= 1_000_000_000:
                return f"{num / 1_000_000_000:.2f}B"
            elif num >= 1_000_000:
                return f"{num / 1_000_000:.2f}M"
            elif num >= 1_000:
                return f"{num / 1_000:.2f}K"
            else:
                return f"{num:.2f}"
        except (TypeError, ValueError):
            return "n/a"

    # === Function 'parsenumber' ===
    @staticmethod
    def parsenumber(s):
        """
        Parses a string representing a scaled number (with suffixes like K, M, or B)
        and returns its numeric float value. Handles common symbols such as "~$" and commas,
        and performs a case-insensitive check for suffixes. Useful for processing user input
        or serialized data from interfaces or APIs.

        Parameters:
        - s (str): A string representing a formatted number (e.g., "1.5K", "2M", "10,000").

        Returns:
        - float or None: The numeric value represented by the input string, or None if parsing fails.
        """
        if not isinstance(s, str):
            return None
        s = s.replace("~$", "").replace(",", "").strip().upper()
        try:
            if s.endswith("M"):
                return float(s[:-1]) * 1_000_000
            elif s.endswith("K"):
                return float(s[:-1]) * 1_000
            else:
                return float(s)
        except ValueError:
            return None
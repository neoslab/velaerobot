# === Import libraries ===
import ctypes
import hashlib
import os
import subprocess
import sys
import tkinter as tk
import urllib.request

# === Import packages ===
from elevate import elevate
from tkinter import messagebox

# === Import dependencies ===
from utils.resolver import PathResolver

# === Define 'elevate' ===
try:
    if not ctypes.windll.shell32.IsUserAnAdmin():
        elevate(show_console=False)
except OSError as elevate_error:
    if hasattr(elevate_error, 'winerror') and elevate_error.winerror == 1223:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Permission Denied", "Administrator privileges are required.\nYou canceled the elevation prompt.\nPlease restart the app and accept the UAC prompt.")
        sys.exit(1)
    else:
        raise


# === Class 'SvgToPngConverter' ===
class SvgToPngConverter:
    """
    This class provides functionality for downloading SVG files from a given URL and converting them to PNG
    format using Inkscape. It handles file naming through hashing, creates required directories automatically,
    and invokes Inkscape in headless mode to perform the rasterization. The class is useful for automated
    icon generation pipelines, asset preparation for GUIs, or conversion tools where PNG assets are required.

    Parameters:
    - None (see initializer for configuration)

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self, size: int = 32, inkscape_path: str | None = None):
        """
        Initializes an instance of the SvgToPngConverter, setting the desired output size for PNG images and
        determining the executable path for Inkscape. If a custom path is not provided, the default path is
        resolved dynamically using PathResolver. Also ensures the existence of required in/output directories
        for SVG and PNG files.

        Parameters:
        - size (int): Width and height (in pixels) of the output PNG images. Default is 32.
        - inkscape_path (str | None): Optional. Full path to the Inkscape executable. If None, the default is resolved.

        Returns:
        - None
        """
        self.size = size
        self.svgdir = PathResolver.fullpathsvg()
        self.pngdir = PathResolver.fullpathpng()
        os.makedirs(self.svgdir, exist_ok=True)
        os.makedirs(self.pngdir, exist_ok=True)
        self.inkscape_path = inkscape_path or PathResolver.pathabsolute(os.path.join("libraries", "inkscape", "App", "Inkscape", "bin", "inkscape.exe"))

    # === Function 'safeconvert' ===
    def safeconvert(self, svg_path: str, png_path: str) -> bool:
        """
        Converts a given SVG file to PNG using Inkscape in command-line mode. Handles subprocess execution
        silently without opening a new window, and captures any output or errors for debugging purposes.
        This function ensures the operation does not raise exceptions if the conversion fails and logs
        any errors encountered during execution.

        Parameters:
        - svg_path (str): Full path to the input SVG file to be converted.
        - png_path (str): Full destination path where the resulting PNG will be saved.

        Returns:
        - bool: True if conversion was successful; False if an error occurred or Inkscape failed.
        """
        try:
            result = subprocess.run(
                [
                    self.inkscape_path,
                    svg_path,
                    "--export-type=png",
                    f"--export-filename={png_path}",
                    f"--export-width={self.size}",
                    f"--export-height={self.size}"
                ],
                creationflags=subprocess.CREATE_NO_WINDOW,
                capture_output=True,
                check=False
            )

            if result.returncode != 0:
                print(f"[ERROR] Inkscape conversion failed:\n{result.stderr.decode(errors='ignore')}")
                return False

            return True

        except Exception as e:
            print(f"[ERROR] Failed to run Inkscape: {e}")
            return False

    # === Function 'convertsvg' ===
    def convertsvg(self, url: str) -> str:
        """
        Downloads an SVG file from the given URL, stores it locally using a hashed filename, and converts it
        to PNG using the safeconvert method. Ensures that existing files are not re-downloaded or overwritten
        unnecessarily. This method simplifies the full flow of fetching a remote vector icon and rendering
        it to a raster image suitable for use in applications or web platforms.

        Parameters:
        - url (str): The URL of the SVG file to download and convert.

        Returns:
        - str: Full path to the generated PNG file. Returns an empty string if the process fails at any stage.
        """
        try:
            name = hashlib.md5(url.encode()).hexdigest()
            svg_path = os.path.join(self.svgdir, f"{name}.svg")
            png_path = os.path.join(self.pngdir, f"{name}.png")

            if not os.path.exists(svg_path):
                print(f"[INFO] Downloading SVG: {url}")
                urllib.request.urlretrieve(url, svg_path)

            if not os.path.exists(png_path):
                print(f"[INFO] Converting to PNG: {png_path}")
                if not self.safeconvert(svg_path, png_path):
                    return ""

            return png_path

        except Exception as e:
            print(f"[ERROR] SVG conversion failed for {url}: {e}")
            return ""
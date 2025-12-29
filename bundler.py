# === Import libraries ===
import os
import platform
import shutil
import subprocess
import sys


# === Class 'ExeBuilder' ===
class ExeBuilder:
    """
    The ExeBuilder class automates the process of building a standalone executable from a Python script using PyInstaller.
    It is designed to clean previous builds, bundle application assets, set an icon, and generate a self-contained executable
    for distribution. This class supports cross-platform compatibility and dynamically adjusts parameters such as path separators
    based on the host operating system. It is especially useful for packaging Python GUI applications or scripts into single-file executables.

    Parameters:
    - pathapp (str): The path to the main Python file to be compiled into an executable.
    - nameapp (str): The desired name for the resulting executable.
    - assets (list[str]): A list of asset paths to include in the build (e.g., folders, data files).
    - iconpath (str): Path to the icon file to embed into the executable (Windows only).

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self, pathapp="main.py", nameapp="VelAerobot", assets=None, iconpath="assets/images/logos/icon.ico"):
        """
        Initializes an instance of the ExeBuilder class, storing the key build parameters for later use.
        It automatically sets default values for application path, name, asset directories, and icon path if not provided.
        Additionally, it determines the correct file separator (`:` or `;`) depending on the operating system to ensure
        compatibility with PyInstaller command syntax.

        Parameters:
        - pathapp (str): The file path of the Python script to convert into an executable.
        - nameapp (str): The name of the resulting executable.
        - assets (list[str] or None): A list of asset directories to be bundled; defaults to ["assets"].
        - iconpath (str): File path to the icon to be used for the executable on Windows platforms.

        Returns:
        - None
        """
        self.pathapp = pathapp
        self.nameapp = nameapp
        self.assets = assets if assets else ["assets"]
        self.iconpath = os.path.abspath(iconpath) if iconpath else None
        self.sepdata = ";" if platform.system() == "Windows" else ":"

    # === Function 'cleanbuild' ===
    def cleanbuild(self):
        """
        Cleans up all previous PyInstaller build artifacts such as the `build` and `dist` directories
        and the `.spec` file. This ensures a fresh and conflict-free environment for a new build.
        It checks whether each target exists and handles both files and directories safely and efficiently.

        Parameters:
        - None

        Returns:
        - None
        """
        for item in ["build", "dist", f"{self.nameapp}.spec"]:
            if os.path.exists(item):
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)

    # === Function 'buildexec' ===
    def buildexec(self):
        """
        Builds the executable by assembling the appropriate PyInstaller command based on the provided
        parameters. This includes asset inclusion, icon support for Windows, and naming customization.
        The function first clears previous build data, then prepares the necessary command-line arguments,
        runs PyInstaller via subprocess, and finally checks and reports the success or failure of the build.

        Parameters:
        - None

        Returns:
        - None
        """
        self.cleanbuild()
        assetargs = []
        for asset in self.assets:
            target = os.path.basename(asset)
            assetargs.append(f"--add-data={asset}{self.sepdata}{target}")

        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--noconfirm",
            "--windowed",
            "--name", self.nameapp,
        ]

        if platform.system() == "Windows" and os.path.exists(self.iconpath):
            cmd += ["--icon", self.iconpath]

        cmd += assetargs
        cmd.append(self.pathapp)

        result = subprocess.run(cmd)
        exename = f"{self.nameapp}.exe" if platform.system() == "Windows" else self.nameapp
        exepath = os.path.join("dist", exename)
        if result.returncode == 0 and os.path.exists(exepath):
            print(f"\nBuild successful! Executable created at: {exepath}")
        else:
            print(f"\nBuild failed. See above output for details.")


# === Callback ===
if __name__ == "__main__":
    """ 
    Entry point for standalone execution. Instantiates the ExeBuilder class with specified parameters 
    and invokes the build process to create the executable. This section is designed to be used when 
    the script is run directly and not imported as a module. The icon and asset folders are passed explicitly.

    Parameters:
    - None

    Returns:
    - None
    """
    builder = ExeBuilder(
        pathapp="main.py",
        nameapp="VelAerobot",
        assets=["assets", "libraries"],
        iconpath="assets/images/logos/icon.ico"
    )
    builder.buildexec()
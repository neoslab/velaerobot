# === Import libraries ===
import tkinter as tk
import threading

# === Import packages ===
from sqlalchemy.exc import SQLAlchemyError
from tkinter import TclError
from tkinter import ttk
from typing import Callable
from typing import Optional

# === Import dependencies ===
from monitoring.listener import LiquidityScraper


# === Class 'SyncPopup' ===
class SyncPopup:
    """
    The SyncPopup class handles the graphical user interface (GUI) and logic for synchronizing
    liquidity pool data from a remote source using a background thread. It creates a modal
    progress popup using Tkinter, displaying dynamic updates during synchronization and running
    the scraper asynchronously to keep the UI responsive. This class is especially useful for
    desktop apps that require real-time data sync without blocking the main UI.

    Parameters:
    - hookcallback (Callable[[], None]): A callback function to be executed once sync is complete.
    - datapath (str): The path to the local data store or configuration.
    - maxdelay (int): Maximum delay in seconds before timeout (default: 3600).

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self, hookcallback: Callable[[], None], datapath: str, maxdelay: int = 3600) -> None:
        """
        Initializes the SyncPopup instance with required UI elements and sync configuration.
        Sets up core attributes including the callback hook, data path, and total progress steps.
        Prepares the Tkinter root window but does not display it until `syncstart()` is called.

        Parameters:
        - hookcallback (Callable[[], None]): Function to call when synchronization completes.
        - datapath (str): String path pointing to the local data directory or configuration.
        - maxdelay (int): Optional maximum delay for sync process timeout, in seconds.

        Returns:
        - None
        """
        self.hookcallback = hookcallback
        self.datapath = datapath
        self.maxdelay = maxdelay
        self.total_pages = 48
        self.root: tk.Tk = tk.Tk()
        self.labelstatic: Optional[tk.Label] = None
        self.labeldynamic: Optional[tk.Label] = None
        self.progress: Optional[ttk.Progressbar] = None

    # === Function 'threadstart' ===
    def threadstart(self) -> None:
        """
        Starts the data synchronization process in a separate background thread
        to avoid freezing the user interface. The thread executes the `syncexec()`
        method, which handles data scraping and progress updates asynchronously.

        Parameters:
        - None

        Returns:
        - None
        """
        threading.Thread(target=self.syncexec, daemon=True).start()

    # === Function 'threadprogress' ===
    def threadprogress(self, message: str, step: int) -> None:
        """
        Updates the popup's progress bar and message label with new synchronization information.
        This function is typically called from the UI thread via `after()` to reflect changes
        in real-time as the sync operation advances.

        Parameters:
        - message (str): The current status message to display.
        - step (int): The progress step to set on the progress bar.

        Returns:
        - None
        """
        if self.labeldynamic:
            self.labeldynamic.config(text=message)
        if self.progress:
            self.progress["value"] = step

    # === Function 'threadcallback' ===
    @staticmethod
    def threadcallback(func: Callable) -> None:
        """
        A static utility method used to call a function from the main UI thread
        using the Tkinter `after()` mechanism. Ensures thread-safe interaction
        between background operations and the UI.

        Parameters:
        - func (Callable): The function to execute.

        Returns:
        - None
        """
        func()

    # === Function 'syncstart' ===
    def syncstart(self) -> None:
        """
        Initializes and displays the synchronization popup window.
        Sets up the layout, fonts, labels, and progress bar, then
        launches the background sync process. This function also centers
        the popup on the user's screen and locks it to the foreground.

        Parameters:
        - None

        Returns:
        - None
        """
        self.root.title("Sync in Progress")
        self.root.resizable(False, False)
        self.root.configure(bg="#0d0d0d")
        self.root.attributes("-topmost", True)

        width, height = 420, 150
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.labelstatic = tk.Label(
            self.root,
            anchor="w",
            bg="#0d0d0d",
            fg="white",
            font=("Arial", 11, "bold"),
            justify="left",
            text="Syncing pools from server"
        )

        self.labeldynamic = tk.Label(
            self.root,
            anchor="w",
            bg="#0d0d0d",
            fg="#cccccc",
            font=("Arial", 10),
            justify="left",
            text="Waiting"
        )

        self.labelstatic.pack(fill="x", padx=20, pady=(15, 0))
        self.labeldynamic.pack(fill="x", padx=20, pady=(4, 10))

        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=self.total_pages)
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.progress["value"] = 0

        self.root.after(100, SyncPopup.threadcallback, self.threadstart)
        self.root.mainloop()

    # === Function 'syncexec' ===
    def syncexec(self) -> None:
        """
        Executes the data synchronization logic in a background thread.
        Instantiates a `LiquidityScraper` and calls its `scrapeall` method,
        passing a callback to update UI progress. Upon completion or error,
        it signals the main thread to close the popup and call the final hook.

        Parameters:
        - None

        Returns:
        - None
        """
        try:
            scraper = LiquidityScraper()

            # === Function 'updateprogress' ===
            def updateprogress(message: str, step: int) -> None:
                """
                A nested callback function used to update the UI with
                progress information during scraping. It safely posts
                progress to the main thread using `after()` to ensure
                thread safety with Tkinter.

                Parameters:
                - message (str): Current operation or pool being synced.
                - step (int): Current step count out of total expected steps.

                Returns:
                - None
                """
                try:
                    self.root.after(0, self.threadprogress, message, step)
                except TclError:
                    pass

            scraper.scrapeall(updatecallback=updateprogress)
        except (SQLAlchemyError, RuntimeError):
            pass
        finally:
            try:
                self.root.after(0, SyncPopup.threadcallback, self.syncfinish)
            except TclError:
                pass

    # === Function 'syncfinish' ===
    def syncfinish(self) -> None:
        """
        Cleans up the synchronization popup once the scraping process completes.
        Stops the progress bar, destroys the Tkinter window, and invokes
        the final user-defined callback function. This marks the end of the sync lifecycle.

        Parameters:
        - None

        Returns:
        - None
        """
        print("[INFO] Sync finished")
        if self.progress:
            self.progress.stop()
        self.root.destroy()
        self.hookcallback()
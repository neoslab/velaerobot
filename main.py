# === Import libraries ===
import hashlib
import os
import json
import sys
import tkinter as tk

# === Import packages ===
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker
from tkinter import PhotoImage
from tkinter import messagebox
from tkinter import ttk
from web3 import Web3

# === Import dependencies ===
from monitoring.handler import SyncHandler
from monitoring.sync import SyncPopup
from utils.coingecko import CoinGecko
from utils.ethereum import EthereumWallet
from utils.models import AerodromePool
from utils.models import LiquidityLogs
from utils.models import StoreBase
from utils.models import VelodromePool
from utils.resolver import PathResolver
from utils.scaler import NumberScaler

# === Define 'PATHCONFIG' ===
PATHCONFIG = PathResolver.pathabsolute("config")

# === Define 'PATHPNG' ===
PATHPNG = PathResolver.fullpathpng()

# === Define 'PATHSVG' ===
PATHSVG = PathResolver.fullpathsvg()

# === Define 'PATHDATA' ===
PATHDATA = PathResolver.pathstorage()

# === Define 'PATHPROTOFILE' ===
PATHPROTOFILE = PathResolver.pathprotocol()

# === Define 'PATHCONFIGFILE' ===
PATHCONFIGFILE = PathResolver.pathconfig()


# === Class 'ThemedApp' ===
class ThemedApp(tk.Tk):
    """
    This class defines a themed Tkinter-based graphical interface application called VelAerobot.
    It is designed to display and manage liquidity data from Velodrome and Aerodrome pools,
    enabling real-time viewing, filtering, and interacting with blockchain-related information.
    The interface uses SQLAlchemy for data persistence, Web3 for Ethereum interactions, and CoinGecko for ETH pricing.

    Parameters:
    - None (inherits from tk.Tk and initializes internally)

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self):
        """
        Initializes the ThemedApp GUI and sets up the visual components,
        protocol configuration, database connection, layout elements, and periodic refresh mechanisms.
        It creates buttons, filters, forms, charts, and navigation elements that allow
        the user to explore and interact with decentralized liquidity data.

        Parameters:
        - None

        Returns:
        - None
        """
        super().__init__()
        self.title("VelAerobot")
        self.geometry("1200x700")

        # === State ===
        self.poolmodel = None
        self.poolquery = 20
        self.pooloffset = 0
        self.scrollframe = None
        self.scrollcanvas = None
        self.filteractive = set()
        self.filternetwork = None
        self.networkvars = tk.StringVar(value="All")
        self.networklist = None
        self.searchtext = tk.StringVar()
        self.confapps = PATHCONFIGFILE
        self.activefilterbutton = None
        self.scrollloop = None
        self.hashcode = "9llp89dd56e88d19e3f036be4a0bdcc9"
        self.after(120000, self.startperiodic, True)
        self.imagecache = []

        # === DB setup ===
        engine = create_engine(f"sqlite:///{PATHDATA}")
        StoreBase.metadata.create_all(engine)
        datasession = sessionmaker(bind=engine)
        self.dbsession = datasession()
        self.loadmore = False

        # === Settings ===
        settings = self.protoload()
        protocoldefault = settings.get("protocol", "Velodrome")
        self.protocolvars = tk.StringVar(value=protocoldefault)

        # === Theme ===
        self.bg = "#0d0d0d"
        self.card = "#1a1a1a"
        self.fg = "#ffffff"
        self.sub = "#888888"
        self.blue = "#4ea1f2"
        self.border = "#333333"
        self.configure(bg=self.bg)

        # === Top Bar ===
        self.topbar = tk.Frame(self, bg=self.bg)
        self.topbar.pack(fill="x", pady=(8, 0))
        tk.Frame(self, height=1, bg=self.border).pack(fill="x", padx=10, pady=10)

        # === Filter Bar ===
        self.filterbar = tk.Frame(self, bg=self.bg)
        self.filterbar.pack(fill="x", pady=(5, 10), padx=10)
        self.filterleft = tk.Frame(self.filterbar, bg=self.bg)
        self.filterleft.pack(side="left", padx=(0, 10))

        # === Network List ===
        self.networks = ["OP Mainnet", "Mode", "Metal L2", "Fraxtal", "Soneium", "Superseed", "Swellchain", "Unichain", "Celo"]

        # === Protocol Select ===
        if protocoldefault == "Velodrome":
            self.buttonnetwork = tk.Button(self.filterleft, activebackground="#353535", activeforeground=self.fg, bd=0, bg="#454545", command=self.networktoogle, fg=self.fg, font=("Arial", 9), padx=14, pady=8, relief="flat", text="All Chains \u25BC")
            self.buttonnetwork.pack(side="left", padx=4, pady=2)

        # === Filters Options ===
        self.addsearchfilters()

        # === Reset Button ===
        self.buttonreset = tk.Button(self.filterleft, activebackground="#9d7e22", activeforeground=self.fg, bd=0, bg="#ba8730", command=self.resetallfilters, fg=self.fg, font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=8, relief="flat", text="Reset")
        self.buttonreset.pack(side="left", padx=5, pady=2)

        # === Search Form ===
        self.filterright = tk.Frame(self.filterbar, bg=self.bg)
        self.filterright.pack(side="right")
        entrywrapper = tk.Frame(self.filterright, height=48, width=300, bg=self.bg)
        entrywrapper.pack_propagate(False)
        entrywrapper.pack(side="right", padx=5, pady=2)

        self.searchtext.set("Symbol or address…")
        searchentry = tk.Entry(entrywrapper, bg=self.card, fg="#a1a1a1", font=("Arial", 10), highlightbackground="#757575", highlightcolor="#757575", highlightthickness=1, insertbackground=self.fg, relief="flat", textvariable=self.searchtext)
        searchentry.pack(fill="both", expand=True, padx=6, pady=6)
        searchentry.bind("<FocusIn>", self.placeholderclear)
        searchentry.bind("<FocusOut>", self.placeholderback)
        searchentry.bind("<Return>", self.fetchsearch)

        # === Logo and Navigation ===
        logopath = self.resourcepath("assets/images/logos/logo.png")
        logoload = PhotoImage(file=logopath)
        self.logosrc = logoload.subsample(max(logoload.width() // 32, 1), max(logoload.height() // 32, 1))
        self.logolabel = tk.Label(self.topbar, image=self.logosrc, bg=self.bg)
        self.logolabel.pack(side="left", padx=10, pady=5)

        # === Navigation Buttons ===
        self.navbuttons = tk.Frame(self.topbar, bg=self.bg)
        self.navbuttons.pack(side="left", padx=(5, 0))

        self.buttonliquidity = self.buttonsnavbar("Liquidity", self.showliquidity)
        self.buttonstacked = self.buttonsnavbar("Stacked", self.showstacked)
        self.buttonsettings = self.buttonsnavbar("Settings", self.popupsettings)

        # === Registration icon and 3 value labels ===
        self.labelregicon = tk.Label(self.navbuttons, text="🔒", font=("Arial", 18, "bold"), bg=self.bg, fg="#c0c0c0")
        self.labelregicon.pack(side="left", padx=(10, 0), pady=2)

        self.stackvalue = tk.Label(self.navbuttons, text="Stacked: USD 0.00", font=("Arial", 11), fg=self.sub, bg=self.bg)
        self.stackvalue.pack(side="left", padx=(15, 0))

        self.walletvalue = tk.Label(self.navbuttons, text="Rewards: USD 0.00", font=("Arial", 11), fg=self.sub, bg=self.bg)
        self.walletvalue.pack(side="left", padx=(15, 0))

        self.mnemonicvalue = tk.Label(self.navbuttons, text="Reserve: ETH 0.00", font=("Arial", 11), fg=self.sub, bg=self.bg)
        self.mnemonicvalue.pack(side="left", padx=(15, 0))

        # === Trigger first load and periodic refresh ===
        self.totalstacked()
        self.totalrewards()
        self.totalreserve()
        self.startperiodic(True)

        # === Right Bar ===
        self.rightbar = tk.Frame(self.topbar, bg=self.bg)
        self.rightbar.pack(side="right", padx=(0, 5))

        self.poolcount = tk.Label(self.topbar, bg=self.bg, fg="#959595", font=("Arial", 12, "bold"), text="")
        self.poolcount.pack(side="right", padx=(0, 20))

        self.protobuttons = tk.Frame(self.rightbar, bg=self.bg)
        self.protobuttons.pack(side="left", padx=5, pady=5)
        self.buttonsprotocols()

        # === Sync Now Button ===
        tk.Button(self.rightbar, activebackground="#3f8b0f", activeforeground="#ffffff", bd=0, bg="#52a022", command=self.runsyncnow, fg="#ffffff", font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=6, relief="flat", text="Sync Now").pack(side="left", padx=5, pady=5, ipady=2)

        # === Flush Logs Button ===
        tk.Button(self.rightbar, activebackground="#6e1c2b", activeforeground="#ffffff", bd=0, bg="#c03434", command=self.flushlogs, fg="#ffffff", font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=6, relief="flat", text="Flush Logs").pack(side="left", padx=5, pady=5, ipady=2)

        # === Main ===
        self.mainwrapper = tk.Frame(self, bg=self.bg, padx=10, pady=10)
        self.mainwrapper.pack(fill="both", expand=True)
        self.sections = tk.Frame(self.mainwrapper, bg=self.bg)
        self.sections.pack(fill="both", expand=True)

        if protocoldefault == "Velodrome":
            self.sectionvelo = self.blockvelodrome()
        else:
            self.sectionvelo = self.blockaerodrome()

        self.sectionaero = self.blockstacked()
        self.showliquidity()

    # === Function 'buttonsnavbar' ===
    def buttonsnavbar(self, text, command, parent=None):
        """
        Creates and returns a styled navigation button that triggers the given command.
        Used to display main navigation actions like 'Liquidity', 'Stacked', or 'Settings'
        within the application's top navigation bar. Buttons are customized with
        theme colors, fonts, and spacing to match the application layout.

        Parameters:
        - text (str): The label of the button to display.
        - command (function): The function to invoke when the button is clicked.
        - parent (tk.Frame or None): The parent widget to attach the button to. If None, defaults to self.navbuttons.

        Returns:
        - tk.Button: The created Tkinter Button widget.
        """
        if parent is None:
            parent = self.navbuttons

        btn = tk.Button(parent, activebackground="#6e1c2b", activeforeground="#ffffff", bd=0, bg="#c03434", command=command, fg="#ffffff", font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=8, relief="flat", text=text)
        btn.pack(side="left", padx=4, pady=2)
        return btn

    # === Function 'buttonsfilters' ===
    def buttonsfilters(self, parent, label):
        """
        Creates a toggleable filter button that updates the active pool filters
        when clicked. It changes color to indicate activation, resets pagination,
        clears the scroll frame, and triggers a fresh pool fetch from the database.
        This function enhances UI interactivity for filtering by pool types.

        Parameters:
        - parent (tk.Frame): The container to which the filter button is added.
        - label (str): The name of the filter shown on the button and used as an identifier in logic.

        Returns:
        - tk.Button: The filter button widget configured with click behavior.
        """
        # === Function 'onclick' ===
        def onclick():
            """
            Handles the toggle behavior of a filter button when clicked.
            If the filter is currently active, it removes it from the set and updates
            the button style to inactive. If not active, it adds the filter and updates
            the style to active. After any change, it resets the scroll view and reloads the pool list.

            Parameters:
            - None

            Returns:
            - None
            """
            if label in self.filteractive:
                self.filteractive.remove(label)
                btn.config(bg="#454545")
            else:
                self.filteractive.add(label)
                btn.config(bg="#6e1c2b")

            self.pooloffset = 0
            for widget in self.scrollframe.winfo_children():
                widget.destroy()
            self.fetchpools()

        btn = tk.Button(parent, activebackground="#353535", activeforeground=self.fg, bd=0, bg="#454545", command=onclick, fg=self.fg, font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=8, relief="flat", text=label)
        btn.pack(side="left", padx=4, pady=2)
        return btn

    # === Function 'buttonsprotocols' ===
    def buttonsprotocols(self):
        """
        Dynamically generates protocol-switching buttons (e.g., Velodrome ↔ Aerodrome)
        based on the current protocol selection. When clicked, these buttons update
        the current protocol in the UI and refresh all relevant views accordingly.
        Ensures only the alternate protocol is offered at any time.

        Parameters:
        - None

        Returns:
        - None
        """
        for widget in self.protobuttons.winfo_children():
            widget.destroy()

        currentprotocol = self.protocolvars.get()
        if currentprotocol == "Velodrome":
            tk.Button(self.protobuttons, activebackground="#3f8b0f", activeforeground="#ffffff", bd=0, bg="#52a022", command=lambda: self.protoswitch("Aerodrome"), fg="#ffffff", font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=6, relief="flat", text="Aerodrome").pack(side="left", ipady=2)
        else:
            tk.Button(self.protobuttons, activebackground="#3f8b0f", activeforeground="#ffffff", bd=0, bg="#52a022", command=lambda: self.protoswitch("Velodrome"), fg="#ffffff", font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=6, relief="flat", text="Velodrome").pack(side="left", ipady=2)

    # === Function 'addsearchfilters' ===
    def addsearchfilters(self):
        """
        Adds a series of predefined filter buttons (Basic, Concentrated, etc.) to the UI,
        allowing users to refine the pool list view by pool characteristics. These filters
        are interactive and toggleable, helping users explore data more effectively.
        Filters are added to the left section of the filter bar dynamically.

        Parameters:
        - None

        Returns:
        - None
        """
        labels = ["Basic", "Concentrated", "Stable", "Volatile", "Low TVL", "APR"]
        for label in labels:
            self.buttonsfilters(self.filterleft, label).pack(side="left", padx=5)

    # === Function 'resetsearchfilters' ===
    def resetsearchfilters(self):
        """
        Re-creates and re-renders the 'Reset' button in the filter UI.
        This allows users to clear all currently applied filters and restore
        the full unfiltered view of the pool data. It also visually resets
        all filter-related UI elements to their default appearance.

        Parameters:
        - None

        Returns:
        - None
        """
        self.buttonreset = tk.Button(self.filterleft, activebackground="#9d7e22", activeforeground=self.fg, bd=0, bg="#ba8730", command=self.resetallfilters, fg=self.fg, font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=8, relief="flat", text="Reset")
        self.buttonreset.pack(side="left", padx=5, pady=2)

    # === Function 'resourcepath' ===
    @staticmethod
    def resourcepath(relative_path):
        """
        Resolves and returns the absolute path to a given relative resource file.
        This is particularly useful when the application is bundled with PyInstaller,
        where resources are extracted to a temporary path accessible via sys._MEIPASS.

        Parameters:
        - relative_path (str): The relative path to a resource file within the project.

        Returns:
        - str: The absolute path to the requested resource.
        """
        srcpathbase = getattr(sys, '_MEIPASS', os.path.abspath("."))
        return os.path.join(srcpathbase, relative_path)

    # === Function 'updatepools' ===
    def updatepools(self):
        """
        Updates the label that displays the total number of liquidity pools currently
        loaded in the scrollable interface. This function queries the bound SQLAlchemy
        pool model for the count and reflects that total in the UI. Useful after applying
        filters or fetching new pages of results to keep the count accurate.

        Parameters:
        - None

        Returns:
        - None
        """
        count = self.dbsession.query(self.poolmodel).count()
        self.poolcount.config(text=f"{count} Pools")

    # === Function 'startperiodic' ===
    def startperiodic(self, action):
        """
        Triggers a periodic refresh of all major metrics displayed on the interface,
        including total stacked funds, wallet rewards, and reserve balance. This is
        executed on a timed basis using Tkinter's `after` method, providing real-time
        data updates without blocking the GUI thread.

        Parameters:
        - action (bool): If True, executes the updates and schedules another refresh.

        Returns:
        - None
        """
        if action is True:
            self.totalstacked()
            self.totalrewards()
            self.totalreserve()
            self.after(120000, self.startperiodic, True)

    # === Function 'totalstacked' ===
    def totalstacked(self):
        """
        Calculates and displays the total value of stacked liquidity based on current
        ETH price data fetched from CoinGecko. It queries the local database for total
        stacked ETH, converts it to USD, and updates the appropriate UI label. If any
        error occurs (database or API), a fallback message is shown instead.

        Parameters:
        - None

        Returns:
        - None
        """
        try:
            totalstack = self.dbsession.query(func.sum(LiquidityLogs.stacked)).scalar() or 0
            ethrate = CoinGecko.ethusd()
            self.stackvalue.config(text=f"Stacked: USD {totalstack * ethrate:,.2f}")
        except Exception as e:
            print(f"[ERROR] Stack total: {e}")
            self.stackvalue.config(text="Total: USD --")

    # === Function 'totalrewards' ===
    def totalrewards(self):
        """
        Retrieves and displays the ETH balance of the configured Ethereum wallet address,
        then calculates and shows the equivalent USD value using CoinGecko's pricing.
        Reads the wallet address from the config file. If the address or config is missing
        or invalid, the UI label will reflect this with a placeholder.

        Parameters:
        - None

        Returns:
        - None
        """
        try:
            if not os.path.exists(PATHCONFIGFILE):
                self.walletvalue.config(text="Rewards: USD --")
                return

            with open(PATHCONFIGFILE, "r") as f:
                data = json.load(f)
                walletaddr = data.get("wallet", "").strip()

            if not walletaddr:
                self.walletvalue.config(text="Rewards: USD --")
                return

            ethrate = CoinGecko.ethusd()
            w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
            address = Web3.to_checksum_address(walletaddr)
            balance_wei = w3.eth.get_balance(address)
            balance_eth = w3.from_wei(balance_wei, 'ether')

            self.walletvalue.config(text=f"Rewards: USD {float(balance_eth) * ethrate:,.2f}")
        except Exception as e:
            print(f"[ERROR] Wallet value: {e}")
            self.walletvalue.config(text="Rewards: USD --")

    # === Function 'totalreserve' ===
    def totalreserve(self):
        """
        Calculates and displays the ETH reserve associated with the wallet's mnemonic seed.
        It first loads the mnemonic from the config file, then initializes an EthereumWallet
        object and fetches the wallet balance. The value is converted to USD using
        CoinGecko pricing and shown in the interface. On failure, a fallback message is used.

        Parameters:
        - None

        Returns:
        - None
        """
        try:
            if not os.path.exists(PATHCONFIGFILE):
                self.mnemonicvalue.config(text="Reserve: ETH --")
                return

            with open(PATHCONFIGFILE, "r") as f:
                data = json.load(f)
                mnemonic = data.get("mnemonic", "").strip()

            if not mnemonic:
                self.mnemonicvalue.config(text="Reserve: ETH --")
                return

            ethrate = CoinGecko.ethusd()
            wallet = EthereumWallet(mnemonic)
            balance = wallet.balance()
            self.mnemonicvalue.config(text=f"Reserve: ETH {balance * ethrate:,.2f}")
        except Exception as e:
            print(f"[ERROR] Mnemonic value: {e}")
            self.mnemonicvalue.config(text="Reserve: ETH --")

    # === Function 'flushswitch' ===
    def flushswitch(self, action):
        """
        Deletes all liquidity logs from the database after user confirmation. This function
        is triggered by the Flush Logs button and ensures irreversible deletion is handled
        safely. After clearing the records, it resets related UI blocks to reflect the change,
        including refreshing the stacked liquidity block if present.

        Parameters:
        - action (bool): If True, initiates the deletion process after confirmation.

        Returns:
        - None
        """
        if action is True:
            confirm = tk.messagebox.askyesno(title="Confirm Flush", message="Are you sure you want to delete all liquidity logs?\nThis action is irreversible.")
            if not confirm:
                return

            try:
                numdeleted = self.dbsession.query(LiquidityLogs).delete()
                self.dbsession.commit()
                tk.messagebox.showinfo("Flush Completed", f"{numdeleted} log entries deleted.")

                self.stopscrollloop()
                if self.sectionaero:
                    self.sectionaero.destroy()
                    self.sectionaero = None

                self.sectionaero = self.blockstacked()
                self.sectionaero.pack(fill="both", expand=True)

                if self.sectionvelo:
                    self.sectionvelo.pack_forget()

            except Exception as e:
                tk.messagebox.showerror("Flush Failed", str(e))

    # === Function 'flushlogs' ===
    def flushlogs(self):
        """
        Triggers the log flush operation by scheduling a short-delay call to `flushswitch`.
        Intended to be used as a button callback for safely starting the log deletion process.
        Ensures that database cleanup is initiated without blocking the UI thread directly.

        Parameters:
        - None

        Returns:
        - None
        """
        action = True
        self.after(100, self.flushswitch, action)

    # === Function 'resetallfilters' ===
    def resetallfilters(self):
        """
        Resets all active pool filters, including search input, chain filters, and button states.
        It clears visual highlights from filter buttons and restores their default color.
        After resetting, it also clears the scroll frame and triggers a fresh pool fetch
        to reflect the unfiltered state.

        Parameters:
        - None

        Returns:
        - None
        """
        self.filteractive = set()
        self.filternetwork = None
        self.searchtext.set("")

        if hasattr(self, "buttonnetwork") and self.protocolvars.get() == "Velodrome":
            self.buttonnetwork.config(text="All Chains ▼")

        for widget in self.filterleft.winfo_children():
            if isinstance(widget, tk.Button) and widget["text"] not in ["Reset", "All Chains ▼"]:
                widget.config(bg="#454545")

        self.pooloffset = 0
        if self.scrollframe:
            for widget in self.scrollframe.winfo_children():
                widget.destroy()

        self.fetchpools()

    # === Function 'placeholderclear' ===
    def placeholderclear(self, _event):
        """
        Clears the placeholder text in the search entry when the user focuses the field.
        If the current text equals the default placeholder ("Symbol or address…"), it is removed
        to allow user input. This improves UX for input fields with initial guide text.

        Parameters:
        - _event (tk.Event): The focus-in event object (unused but required by bind).

        Returns:
        - None
        """
        if self.searchtext.get() == "Symbol or address…":
            self.searchtext.set("")

    # === Function 'placeholderback' ===
    def placeholderback(self, _event):
        """
        Restores the placeholder text in the search field if the input is left empty
        when focus is lost. This keeps the UI intuitive and indicates the purpose of the input box
        when it's not in use.

        Parameters:
        - _event (tk.Event): The focus-out event object (unused but required by bind).

        Returns:
        - None
        """
        if not self.searchtext.get().strip():
            self.searchtext.set("Symbol or address…")

    # === Function 'protoload' ===
    @staticmethod
    def protoload():
        """
        Loads the current protocol configuration from the JSON settings file. If the file doesn't exist,
        a default value of 'Velodrome' is returned. This function ensures the GUI starts with the correct
        protocol context based on previous sessions.

        Parameters:
        - None

        Returns:
        - dict: A dictionary containing the saved protocol value (e.g., {"protocol": "Velodrome"}).
        """
        os.makedirs(PATHCONFIG, exist_ok=True)
        if os.path.exists(PATHPROTOFILE):
            with open(PATHPROTOFILE, "r") as f:
                return json.load(f)
        return {"protocol": "Velodrome"}

    # === Function 'protosave' ===
    def protosave(self):
        """
        Saves the currently selected protocol (Velodrome or Aerodrome) to a JSON configuration file
        for persistence across sessions. Creates the config directory if it doesn't exist,
        then writes the selected protocol to disk.

        Parameters:
        - None

        Returns:
        - None
        """
        os.makedirs(PATHCONFIG, exist_ok=True)
        with open(PATHPROTOFILE, "w") as f:
            json.dump({"protocol": self.protocolvars.get()}, f)

    # === Function 'protoswitch' ===
    def protoswitch(self, value):
        """
        Switches the application context between Velodrome and Aerodrome modes. Updates protocol state,
        saves the selection, refreshes UI sections and filters, and reloads the appropriate pool blocks.
        This function ensures the interface dynamically adapts to the selected protocol.

        Parameters:
        - value (str): Either "Velodrome" or "Aerodrome", indicating the new protocol to activate.

        Returns:
        - None
        """
        self.protocolvars.set(value)
        self.protosave()

        if self.sectionvelo:
            self.sectionvelo.destroy()
        if self.sectionaero:
            self.sectionaero.destroy()

        if value == "Velodrome":
            self.sectionvelo = self.blockvelodrome()
            self.sectionvelo.pack(fill="both", expand=True)
        else:
            self.sectionaero = self.blockaerodrome()
            self.sectionaero.pack(fill="both", expand=True)

        self.updatepools()
        self.buttonsprotocols()

        for widget in self.filterleft.winfo_children():
            widget.destroy()

        self.filteractive = set()
        self.filternetwork = None

        if value == "Velodrome":
            self.networks = ["OP Mainnet", "Mode", "Metal L2", "Fraxtal", "Soneium", "Superseed", "Swellchain", "Unichain", "Celo"]
            self.networkvars = tk.StringVar(value="All")
            self.buttonnetwork = self.chainslist()
            self.buttonnetwork.pack(side="left", padx=4, pady=2)

        self.addsearchfilters()
        self.resetsearchfilters()

    # === Function 'networktoogle' ===
    def networktoogle(self):
        """
        Displays a floating list of available blockchain networks under the 'All Chains ▼' button.
        Allows the user to choose a specific chain to filter liquidity pools by network.
        Clicking a network applies the filter and updates the button text accordingly.

        Parameters:
        - None

        Returns:
        - None
        """
        if self.networklist is not None and self.networklist.winfo_exists():
            self.networklist.destroy()
            return

        self.networklist = tk.Toplevel(self)
        self.networklist.overrideredirect(True)
        self.networklist.configure(bg="#1a1a1a", bd=0)
        self.networklist.lift()

        x = self.buttonnetwork.winfo_rootx()
        y = self.buttonnetwork.winfo_rooty() + self.buttonnetwork.winfo_height()
        self.networklist.geometry(f"+{x}+{y}")

        # === Function 'networkselector' ===
        def networkselector(selected_name):
            """
            Callback function triggered when a network is selected from the dropdown list.
            It applies the corresponding network filter using the `networkfiltering` method,
            or clears it if "All" is selected. After updating the filter, the dropdown window
            is closed and destroyed.

            Parameters:
            - selected_name (str): The name of the selected network from the list (e.g., "OP Mainnet" or "All").

            Returns:
            - None
            """
            self.networkfiltering(None if selected_name == "All" else selected_name)
            self.networklist.destroy()

        for netname in ["All"] + self.networks:
            btn = tk.Button(self.networklist, activebackground="#353535", activeforeground=self.fg, anchor="w", bd=0, bg="#1a1a1a", command=lambda n=netname: networkselector(n), fg=self.fg, font=("Arial", 9), padx=10, pady=4, relief="flat", text=netname)
            btn.pack(fill="x")

    # === Function 'networkfiltering' ===
    def networkfiltering(self, value):
        """
        Applies a network filter to the pool view based on the selected blockchain name.
        Updates the filter state, changes the chain dropdown label accordingly,
        resets pagination and UI content, and triggers a fresh fetch of pools from the database.

        Parameters:
        - value (str or None): The name of the selected network (e.g., "OP Mainnet") or None to clear the filter.

        Returns:
        - None
        """
        self.filternetwork = value
        label = "All Chains ▼" if value is None else f"{value} ▼"
        self.buttonnetwork.config(text=label)
        self.pooloffset = 0
        for widget in self.scrollframe.winfo_children():
            widget.destroy()
        self.fetchpools()

    # === Function 'aftersync' ===
    def aftersync(self):
        """
        Callback method used after a sync operation is completed.
        Clears the current scroll frame and reloads the pool data to reflect
        any updated entries. Ensures the UI is consistent with the new state of the database.

        Parameters:
        - None

        Returns:
        - None
        """
        self.pooloffset = 0
        for widget in self.scrollframe.winfo_children():
            widget.destroy()
        self.fetchpools()

    # === Function 'runsyncnow' ===
    def runsyncnow(self):
        """
        Manually triggers a data synchronization using the SyncHandler.
        If an update is available, it opens the SyncPopup to process the sync
        and calls `aftersync` once complete. If no update is found,
        a message is displayed to inform the user.

        Parameters:
        - None

        Returns:
        - None
        """
        syncchecker = SyncHandler(sqlitepath=PATHDATA, maxseconds=0)
        if syncchecker.checkupdate():
            syncpools = SyncPopup(hookcallback=self.aftersync, datapath=PATHDATA)
            syncpools.syncstart()
        else:
            tk.messagebox.showinfo("Sync", "Data is already up to date.")

    # === Function 'poolsanalyzer' ===
    @staticmethod
    def poolsanalyzer(pool) -> tuple[str, str]:
        """
        Analyzes a pool object to determine a score and color code based on liquidity,
        volume, APR, fee level, and type. This score is used for visual badges in the UI,
        providing a quick qualitative summary of each liquidity pool.

        Parameters:
        - pool (object): A pool entry (VelodromePool or AerodromePool) with attributes like tvl, volume, apr, group, and type.

        Returns:
        - tuple[str, str]: A tuple containing the score as a percentage string (e.g., "85%")
          and a color indicator ("green", "yellow", or "red") based on the score.
        """
        score = 0

        # TVL
        tvl = pool.tvl or 0
        if tvl >= 10_000_000:
            score += 30
        elif tvl >= 1_000_000:
            score += 20
        elif tvl >= 100_000:
            score += 10

        # Volume
        volume = pool.volume or 0
        if volume >= 500_000:
            score += 25
        elif volume >= 100_000:
            score += 15
        elif volume >= 10_000:
            score += 5

        # APR
        apr = pool.apr or 0
        if apr < 10:
            score += 25
        elif apr < 30:
            score += 15

        # Fees
        try:
            fee_val = float(pool.group or 0)
            if 0 < fee_val <= 0.1:
                score += 10
            elif 0.1 < fee_val <= 0.5:
                score += 5
        except ValueError:
            pass

        # Pool type
        if pool.type and "stable" in pool.type.lower():
            score += 10

        if score >= 70:
            color = "green"
        elif score >= 40:
            color = "yellow"
        else:
            color = "red"

        return f"{score}%", color

    # === Function 'blockvelodrome' ===
    def blockvelodrome(self):
        """
        Initializes and returns the main UI section displaying Velodrome pools.
        It sets up a scrollable card layout using the VelodromePool model as the data source.
        This function is triggered when the protocol context is set to Velodrome.

        Parameters:
        - None

        Returns:
        - tk.Frame: A wrapper frame containing the scrollable Velodrome pool cards.
        """
        return self.scrollablecards(VelodromePool)

    # === Function 'blockaerodrome' ===
    def blockaerodrome(self):
        """
        Initializes and returns the main UI section displaying Aerodrome pools.
        It reuses the same scrollable card layout mechanism but provides AerodromePool
        as the active model to fetch and display relevant pool data in the UI.

        Parameters:
        - None

        Returns:
        - tk.Frame: A wrapper frame containing the scrollable Aerodrome pool cards.
        """
        return self.scrollablecards(AerodromePool)

    # === Function 'blockstacked' ===
    def blockstacked(self):
        """
        Builds and returns the stacked liquidity section in the interface.
        Destroys existing filter buttons and adds new ones for filtering between
        'Stacked', 'Unstacked', and 'Reset'. Queries the LiquidityLogs model and
        displays all entries matching the selected filter. If no logs exist,
        a placeholder message is shown.

        Parameters:
        - None

        Returns:
        - tk.Frame: A wrapper frame containing the stacked/unstacked liquidity cards or message.
        """
        for widget in self.filterleft.winfo_children():
            widget.destroy()

        # === Function 'stackfilters' ===
        def stackfilters(value):
            """
            Handles the logic for toggling between 'Stacked', 'Unstacked', or full liquidity logs.
            It resets all active filters, optionally applies the selected status filter,
            and triggers a UI refresh to update the stacked deposits view accordingly.

            Parameters:
            - value (str): The selected filter value, which should be one of "Stacked", "Unstacked", or "Reset".

            Returns:
            - None
            """
            self.filteractive = set()
            if value in ("Stacked", "Unstacked"):
                self.filteractive.add(value)
            self.refreshstacked(True)

        tk.Button(self.filterleft, text="Stacked", command=lambda: stackfilters("Stacked"), font=("Arial", 9), bg="#454545", fg=self.fg, padx=14, pady=6, relief="flat").pack(side="left", padx=5)
        tk.Button(self.filterleft, text="Unstacked", command=lambda: stackfilters("Unstacked"), font=("Arial", 9), bg="#454545", fg=self.fg, padx=14, pady=6, relief="flat").pack(side="left", padx=5)
        tk.Button(self.filterleft, text="Reset", command=lambda: stackfilters("Reset"), font=("Arial", 9), bg="#ba8730", fg=self.fg, padx=14, pady=6, relief="flat").pack(side="left", padx=5)

        wrapper, scrollframe, canvas = self.scrollablesections()
        self.scrollframe = scrollframe
        self.scrollcanvas = canvas

        query = self.dbsession.query(LiquidityLogs)
        if "Stacked" in self.filteractive:
            query = query.filter(LiquidityLogs.status == True)
        elif "Unstacked" in self.filteractive:
            query = query.filter(LiquidityLogs.status == False)

        logs = query.order_by(LiquidityLogs.id.desc()).all()

        if not logs:
            message = tk.Label(scrollframe, text="No deposit history found.\n\nYou haven't made any active or past liquidity deposits yet.", font=("Arial", 11), fg="#bbbbbb", bg=self.bg, justify="center", wraplength=500, padx=20, pady=60)
            message.pack(expand=True, fill="both")
            return wrapper

        for log in logs:
            self.cryptocards(
                pool=log, parent=scrollframe, pairs=log.pairs, poolfee=f"{log.group or '0'}%", network=log.network,
                volhead=f"${log.volume:,.2f}" if log.volume else "N/A",
                volquote=f"{log.basebalance or 0:.5f} {log.basename}\n{log.quotebalance or 0:.5f} {log.quotename}",
                feeshead=f"${log.fiat:,.2f}" if log.fiat else "N/A",
                feesquote=f"{log.basefees or 0:.5f} {log.basename}\n{log.quotefees or 0:.5f} {log.quotename}",
                tvlhead=NumberScaler.formatsuffix(log.tvl),
                tvlquote=f"{log.baseprice or 0:.2f} {log.basename}\n{log.quoteprice or 0:.2f} {log.quotename}",
                ratio=f"{log.apr:.2f}%" if log.apr else "0%", showbutton=False, shownetwork=False
            )

        return wrapper

    # === Function 'stopscrollloop' ===
    def stopscrollloop(self):
        """
        Stops the currently active scroll monitoring loop if one exists.
        This is used to prevent multiple simultaneous background scroll watchers
        that could cause duplicate loads or performance issues during infinite scrolling.

        Parameters:
        - None

        Returns:
        - None
        """
        if self.scrollloop is not None:
            self.after_cancel(self.scrollloop)
            self.scrollloop = None

    # === Function 'scrollablesections' ===
    def scrollablesections(self):
        """
        Creates and returns a fully scrollable UI section containing a canvas and an inner frame.
        This structure allows dynamic insertion of widgets and supports mouse wheel scrolling.
        Also binds a resize function to adjust the canvas width on UI changes. Commonly used for
        displaying pool or log entries in card format.

        Parameters:
        - None

        Returns:
        - tuple[tk.Frame, tk.Frame, tk.Canvas]: A tuple containing the wrapper frame, scrollable frame, and canvas.
        """
        wrapper = tk.Frame(self.sections, bg=self.bg)
        wrapper.pack(fill="both", expand=True)
        wrapper.pack_propagate(False)
        canvas = tk.Canvas(wrapper, bg=self.bg, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        canvas.pack_propagate(False)
        scrollbar = tk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        scrollframe = tk.Frame(canvas, bg=self.bg)
        canvaswindow = canvas.create_window((0, 0), window=scrollframe, anchor="nw")

        # === Function 'resizeinner' ===
        def resizeinner(_event=None):
            """
            Adjusts the width of the canvas window to match the canvas size whenever the container is resized.
            Ensures that the scrollable content correctly adapts to changes in the main window layout or parent frame.

            Parameters:
            - _event (tk.Event or None): The triggering resize event (optional, often unused).

            Returns:
            - None
            """
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvaswindow, width=canvas_width)

        scrollframe.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", resizeinner)

        # === Function 'mousewheelactive' ===
        def mousewheelactive(event):
            """
            Handles mouse wheel scrolling for the scrollable canvas.
            Translates the vertical scroll event into a canvas y-axis scroll movement,
            providing a smooth and intuitive scrolling experience in the pool or log sections.
            This function is dynamically bound when the mouse enters the scrollable area.

            Parameters:
            - event (tk.Event): The mouse wheel event containing scroll delta data.

            Returns:
            - None
            """
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        scrollframe.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", mousewheelactive))
        scrollframe.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))
        canvas.configure(yscrollcommand=scrollbar.set)
        return wrapper, scrollframe, canvas

    # === Function 'scrollcanvasargs' ===
    def scrollcanvasargs(self, *_):
        """
        Forces the canvas to trigger a <Configure> event, which prompts a re-layout of the scrollable content.
        This is useful after dynamically inserting elements or resizing the canvas to ensure proper display.

        Parameters:
        - *_: Placeholder for any arguments passed by `after` or `bind` (ignored).

        Returns:
        - None
        """
        self.scrollcanvas.event_generate("<Configure>")

    # === Function 'scrollablecards' ===
    def scrollablecards(self, model):
        """
        Initializes a scrollable section to display liquidity pool cards using a specified model.
        It sets the active model, resets pagination parameters, loads the initial data,
        and attaches scroll monitoring logic to handle infinite loading as the user scrolls.

        Parameters:
        - model (Base): The SQLAlchemy model to use for querying pool data (e.g., VelodromePool or AerodromePool).

        Returns:
        - tk.Frame: A wrapper frame containing the rendered scrollable card section.
        """
        self.poolmodel = model
        self.pooloffset = 0
        self.poolquery = 20
        wrapper, scrollframe, canvas = self.scrollablesections()
        self.scrollcanvas = canvas
        self.scrollframe = scrollframe
        self.fetchpools()
        self.after(100, self.scrollcanvasargs, None)
        self.scrollevents()
        return wrapper

    # === Function 'scrollevents' ===
    def scrollevents(self):
        """
        Attaches a looped scroll-monitoring function to detect when the scroll position
        approaches the bottom of the canvas. If the end is reached and loading is allowed,
        it triggers a fetch for additional pool entries. Ensures seamless infinite scrolling.

        Parameters:
        - None

        Returns:
        - None
        """
        canvas = self.scrollcanvas
        if not canvas:
            return

        # === Function 'scrollposition' ===
        def scrollposition(*args):
            """
            Monitors the vertical scroll position of the canvas to implement infinite scrolling behavior.
            If the scrollbar reaches the bottom (≥99%), and no loading is in progress, it triggers a fetch
            of additional data. This function is looped using `after()` to continuously track the position.

            Parameters:
            - *args (tuple): Optional arguments used to identify loop mode or initialization (e.g., "loop").

            Returns:
            - None
            """
            if args[0] is not None:
                if not self.scrollcanvas or not str(self.scrollcanvas):
                    return

                try:
                    yview = canvas.yview()
                    if yview[1] >= 0.99 and not self.loadmore:
                        self.loadmore = True
                        self.after(500, self.fetchmore, True)
                    self.scrollloop = self.after(1500, scrollposition, "loop")
                except tk.TclError:
                    return

        scrollposition("init")

    # === Function 'fetchsearch' ===
    def fetchsearch(self, _event=None):
        """
        Triggers a new search based on the current input in the search field.
        It resets the pagination, clears all current pool cards from the scrollable area,
        and re-fetches the pools matching the updated search criteria.
        typically triggered when the user presses return in the search box.

        Parameters:
        - _event (tk.Event or None): Optional event parameter from the <Return> key bind.

        Returns:
        - None
        """
        self.pooloffset = 0
        for widget in self.scrollframe.winfo_children():
            widget.destroy()
        self.fetchpools()

    # === Function 'fetchmore' ===
    def fetchmore(self, action):
        """
        Handles the logic for loading additional pools when infinite scroll is active.
        It ensures new data is fetched from the database only when the action flag is True,
        and resets the internal loading state afterward to allow future loads.

        Parameters:
        - action (bool): If True, triggers a data fetch and disables the loading flag after completion.

        Returns:
        - None
        """
        if action is True:
            self.fetchpools()
            self.loadmore = False

    # === Function 'fetchpools' ===
    def fetchpools(self):
        """
        Fetches and displays a batch of liquidity pools based on current filters
        (type, network, search term). Applies pagination, builds SQLAlchemy queries,
        and renders each pool as a card in the scrollable frame. This is the core function
        for listing and refreshing pool data in the interface.

        Parameters:
        - None

        Returns:
        - None
        """
        query = self.dbsession.query(self.poolmodel)
        filters = []

        typecolumn = self.poolmodel.type
        typefilters = []

        if "Basic" in self.filteractive:
            typefilters.append(typecolumn.ilike("%Basic%"))
        if "Concentrated" in self.filteractive:
            typefilters.append(typecolumn.ilike("%Concentrated%"))
        if "Stable" in self.filteractive:
            typefilters.append(typecolumn.ilike("%Stable%"))
        if "Volatile" in self.filteractive:
            typefilters.append(typecolumn.ilike("%Volatile%"))

        if typefilters:
            filters.append(or_(*typefilters))

        if isinstance(self.filternetwork, str) and self.filternetwork.strip():
            filters.append(self.poolmodel.network == self.filternetwork)

        searchquery = self.searchtext.get().strip()
        if searchquery and searchquery != "Symbol or address…":
            filters.append(func.lower(self.poolmodel.pairs).like(f"%{searchquery.lower()}%"))

        for f in filters:
            query = query.filter(f)

        if "Low TVL" in self.filteractive:
            query = query.order_by(self.poolmodel.tvl.asc())
        elif "APR" in self.filteractive:
            query = query.order_by(self.poolmodel.apr.desc())
        else:
            query = query.order_by(self.poolmodel.id)

        pools = query.offset(self.pooloffset).limit(self.poolquery).all()
        if not pools:
            return

        for pool in pools:
            self.cryptocards(
                pool=pool, parent=self.scrollframe, pairs=pool.pairs, poolfee=f"{pool.group or '0'}%",
                network=pool.network, volhead=f"${pool.volume:,.2f}" if pool.volume else "N/A",
                volquote=f"{pool.basebalance or 0:.5f} {pool.basename}\n{pool.quotebalance or 0:.5f} {pool.quotename}",
                feeshead=f"${pool.fiat:,.2f}" if pool.fiat else "N/A",
                feesquote=f"{pool.basefees or 0:.5f} {pool.basename}\n{pool.quotefees or 0:.5f} {pool.quotename}",
                tvlhead=NumberScaler.formatsuffix(pool.tvl),
                tvlquote=f"{pool.baseprice or 0:.2f} {pool.basename}\n{pool.quoteprice or 0:.2f} {pool.quotename}",
                ratio=f"{pool.apr:.2f}%" if pool.apr else "0%", showbutton=True
            )

        self.pooloffset += self.poolquery
        self.updatepools()

    # === Function 'dictpool' ===
    @staticmethod
    def dictpool(pool):
        """
        Serializes a pool object into a dictionary containing all relevant fields,
        including token names, addresses, balances, volume, APR, and URL.
        This is useful when passing structured data between functions like popupstacked.

        Parameters:
        - pool (object): A VelodromePool or AerodromePool instance from the database.

        Returns:
        - dict: A dictionary representation of the pool suitable for JSON or structured display.
        """
        return {
            "pairs": pool.pairs, "basename": pool.basename, "quotename": pool.quotename, "network": pool.network,
            "chainid": pool.chainid, "type": pool.type, "baseaddr": pool.baseaddr, "baselogo": pool.baselogo,
            "basebalance": pool.basebalance, "basefees": pool.basefees, "baseprice": pool.baseprice,
            "quoteaddr": pool.quoteaddr, "quotelogo": pool.quotelogo, "quotebalance": pool.quotebalance,
            "quotefees": pool.quotefees, "quoteprice": pool.quoteprice, "tvl": pool.tvl, "volume": pool.volume,
            "apr": pool.apr, "group": pool.group, "fiat": pool.fiat, "factory": pool.factory, "url": pool.url
        }

    # === Function 'cryptocards' ===
    def cryptocards(self, pool, pairs, poolfee, network, volhead, volquote, feeshead, feesquote, tvlhead, tvlquote, ratio, showbutton=True, shownetwork=True, parent=None):
        """
        Renders a detailed card-style UI component representing a liquidity pool.
        Displays token icons, pair info, volume, fees, TVL, APR, and interactive buttons
        for stacking or unstacking depending on context. Designed for both Velodrome and Aerodrome modes.

        Parameters:
        - pool (object): The pool or log object with all required data fields.
        - pairs (str): Pair name (e.g., "ETH/USDC").
        - poolfee (str): Fee percentage string (e.g., "0.01%").
        - network (str): Network label to display.
        - volhead (str): Headline value for volume (e.g., "$12,000").
        - volquote (str): Subtext for volume breakdown.
        - feeshead (str): Headline value for fees.
        - feesquote (str): Subtext for fee breakdown.
        - tvlhead (str): Headline TVL value.
        - tvlquote (str): Subtext for TVL tokens.
        - ratio (str): APR value (e.g., "24.50%").
        - showbutton (bool): Whether to show the stacking button (default True).
        - shownetwork (bool): Whether to show the network label (default True).
        - parent (tk.Frame or None): Parent container for the card.

        Returns:
        - None
        """
        card = tk.Frame(parent, bg=self.card, padx=15, pady=10, highlightbackground=self.border, highlightthickness=1)
        card.pack(fill="x", expand=True, padx=0, pady=5)
        card.grid_columnconfigure(0, weight=6, uniform="col")
        card.grid_columnconfigure(1, weight=2, uniform="col")
        card.grid_columnconfigure(2, weight=2, uniform="col")
        card.grid_columnconfigure(3, weight=2, uniform="col")
        card.grid_columnconfigure(4, weight=1, uniform="col")

        left = tk.Frame(card, bg=self.card)
        left.grid(row=0, column=0, sticky="w", padx=(0, 10))

        icons = tk.Frame(left, bg=self.card)
        icons.pack(anchor="w")

        srcpathbase = pool.baselogo
        srcpathquote = pool.quotelogo
        srciconbase = None
        srciconquote = None

        if srcpathbase and os.path.exists(srcpathbase):
            srciconbase = PhotoImage(file=srcpathbase)

        if srcpathquote and os.path.exists(srcpathquote):
            srciconquote = PhotoImage(file=srcpathquote)

        if not hasattr(self, 'imagecache'):
            self.imagecache = []

        if srciconbase:
            self.imagecache.append(srciconbase)
            tk.Label(icons, image=srciconbase, bg=self.card).pack(side="left")
        else:
            tk.Label(icons, text="🪙", font=("Arial", 22), bg=self.card, fg=self.fg).pack(side="left")

        if srciconquote:
            self.imagecache.append(srciconquote)
            tk.Label(icons, image=srciconquote, bg=self.card).pack(side="left", padx=2)
        else:
            tk.Label(icons, text="🪙", font=("Arial", 22), bg=self.card, fg=self.fg).pack(side="left", padx=2)

        sentwrap, sentcolor = self.poolsanalyzer(pool)
        badge = tk.Label(icons, bg=sentcolor, fg="#000000" if sentcolor == "yellow" else "#ffffff", font=("Courier New", 9, "bold"), padx=4, pady=1, text=sentwrap, width=5)

        badge.pack(side="left", padx=(8, 0))
        title = tk.Frame(left, bg=self.card)
        title.pack(anchor="w")
        tk.Label(title, text=pairs, font=("Arial", 11, "bold"), fg=self.fg, bg=self.card).pack(side="left")
        tk.Label(title, text=f" {poolfee}", font=("Arial", 9), fg=self.sub, bg=self.card).pack(side="left")

        if hasattr(pool, "network"):
            row = tk.Frame(left, bg=self.card)
            row.pack(anchor="w", pady=(2, 4), fill="x")

            if shownetwork:
                tk.Label(row, text=network.upper(), font=("Arial", 9), fg=self.sub, bg=self.card).pack(side="left")

            if hasattr(pool, "stacked") and isinstance(pool.stacked, (int, float)):
                textstacked = f"Stacked {pool.stacked:.8f} ETH"
                tk.Label(row, text=textstacked, font=("Arial", 9), fg="#bbbbbb", bg=self.card).pack(side="left")

                if hasattr(pool, "priority") or hasattr(pool, "bull") or hasattr(pool, "bear"):
                    extra = tk.Label(card, text=f"Priority: {getattr(pool, 'priority', '—') or '—'} | Bull: {getattr(pool, 'bull', '—') or '—'}s | Bear: {getattr(pool, 'bear', '—') or '—'}s", font=("Arial", 10), fg="#888888", bg=self.card, anchor="w", justify="left")
                    extra.grid(row=1, column=0, columnspan=5, sticky="w", padx=0, pady=0)

        # === Function 'statheader' ===
        def statheader(wrapper, name, val, sub):
            """
            Creates a compact vertical layout containing three stacked labels:
            a title, a bolded value, and a subtitle. This widget structure is used
            to consistently display pool metrics such as Volume, Fees, or TVL inside pool cards.

            Parameters:
            - wrapper (tk.Frame): The parent frame where the stat block will be added.
            - name (str): The title or label for the metric (e.g., "Volume").
            - val (str): The main numeric value to highlight (e.g., "$12,300").
            - sub (str): A subtext or detailed breakdown related to the value.

            Returns:
            - tk.Frame: A frame widget containing the vertically stacked stat elements.
            """
            f = tk.Frame(wrapper, bg=self.card)
            tk.Label(f, text=name, font=("Arial", 9), fg=self.sub, bg=self.card).pack()
            tk.Label(f, text=val, font=("Arial", 10, "bold"), fg=self.fg, bg=self.card).pack()
            tk.Label(f, text=sub, font=("Arial", 9), fg="#666", bg=self.card).pack()
            return f

        statheader(card, "Volume", volhead, volquote).grid(row=0, column=1, sticky="nsew")
        statheader(card, "Fees", feeshead, feesquote).grid(row=0, column=2, sticky="nsew")
        statheader(card, "TVL", tvlhead, tvlquote).grid(row=0, column=3, sticky="nsew")

        right = tk.Frame(card, bg=self.card)
        right.grid(row=0, column=4, sticky="nsew")
        tk.Label(right, text="APR", font=("Arial", 8), fg=self.sub, bg=self.card).pack()
        tk.Label(right, text=ratio, font=("Arial", 11, "bold"), fg=self.fg, bg=self.card).pack()
        
        if showbutton:
            pathiconstack = os.path.join(PathResolver.fullpathicons(), "stack.png")
            if os.path.exists(pathiconstack):
                stackicon = PhotoImage(file=pathiconstack)
                self.imagecache.append(stackicon)
                tk.Button(right, image=stackicon, command=lambda: self.popupstacked(self.dictpool(pool)), bg=self.card, relief="flat", bd=0, highlightthickness=0, activebackground=self.card).pack(pady=5)
        else:
            if hasattr(pool, "status") and pool.status is True:
                pathiconunstack = os.path.join(PathResolver.fullpathicons(), "unstack.png")
                if os.path.exists(pathiconunstack):
                    unstackicon = PhotoImage(file=pathiconunstack)
                    self.imagecache.append(unstackicon)
                    tk.Button(right, image=unstackicon, command=lambda: self.unstackdeposit(pool), bg=self.card, relief="flat", bd=0, highlightthickness=0, activebackground=self.card).pack(padx=(5, 0), pady=5)
            else:
                tk.Label(right, text="Unstacked", font=("Arial", 10), fg="#ff0000", bg=self.card).pack(pady=10)

    # === Function 'checkregistration' ===
    def checkregistration(self):
        """
        Verifies whether the application is registered by checking the stored serial code.
        It loads the serial from the configuration file and compares its MD5 hash against
        a predefined reference hash. Returns True if the hash matches, False if invalid or missing,
        and None if the serial exists but doesn't match the expected value.

        Parameters:
        - None

        Returns:
        - bool or None: True if valid and matches, False if missing, None if incorrect.
        """
        if not os.path.exists(self.confapps):
            return False

        try:
            with open(self.confapps, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return False

        serial = data.get("serial", "").strip()
        if not serial:
            return False

        md5hash = hashlib.md5(serial.encode("utf-8")).hexdigest()
        if md5hash == self.hashcode:
            return True
        else:
            return None

    # === Function 'registrationstatus' ===
    def registrationstatus(self):
        """
        Updates the registration icon in the navigation bar based on the current registration status.
        It calls `checkregistration()` and changes the padlock icon and color accordingly:
        green for valid, grey for unregistered, and red for mismatch or error.

        Parameters:
        - None

        Returns:
        - None
        """
        status = self.checkregistration()
        if status:
            self.labelregicon.config(text="🔓", fg="green")
        elif status is False:
            self.labelregicon.config(text="🔒", fg="#c0c0c0")
        else:
            self.labelregicon.config(text="🔒", fg="red")

    # === Function 'popuploader' ===
    def popuploader(self, title, width, height):
        """
        Creates and displays a modal popup window centered on the screen.
        The popup is configured with a fixed size and a custom background color.
        It returns both the popup reference and its main content wrapper frame,
        ready to be filled with widgets or forms.

        Parameters:
        - title (str): The title of the popup window.
        - width (int): The desired width of the popup.
        - height (int): The desired height of the popup.

        Returns:
        - tuple[tk.Toplevel, tk.Frame]: A tuple containing the popup window and its inner container frame.
        """
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.transient(self)
        popup.grab_set()
        popup.configure(bg=self.bg)
        posx = self.winfo_rootx() + (self.winfo_width() // 2) - (width // 2)
        posy = self.winfo_rooty() + (self.winfo_height() // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{posx}+{posy}")
        outer = tk.Frame(popup, bg=self.bg)
        outer.pack(expand=True, fill="both")
        return popup, outer

    # === Function 'popupstacked' ===
    def popupstacked(self, pool=None):
        """
        Opens a modal popup window to allow the user to inject liquidity (i.e., create a new deposit).
        Pre-fills the ETH equivalent from a default USD amount, shows input fields for bull/bear timing,
        and allows submission if configuration is valid. Upon confirmation, stores the deposit in the database
        and shows a progress bar simulating a network stack.

        Parameters:
        - pool (dict or None): Dictionary with pool metadata for the deposit (or None if uninitialized).

        Returns:
        - None
        """
        from typing import Literal
        popup, outer = self.popuploader("New Deposit", 400, 480)
        inner = tk.Frame(outer, bg=self.bg, width=340, height=420)
        inner.place(relx=0.5, rely=0.5, anchor="center")
        inner.pack_propagate(False)

        usdvar = tk.StringVar()
        ethvar = tk.StringVar()
        priorityvar = tk.StringVar(value=pool["basename"] if pool else "")
        bullvar = tk.StringVar()
        bearvar = tk.StringVar()

        ethrate = CoinGecko.ethusd()
        if not isinstance(ethrate, (int, float)) or ethrate <= 0:
            messagebox.showerror("Error", "Unable to retrieve ETH price.")
            popup.destroy()
            return

        usdvar.set("100")
        ethvar.set(f"{100 / ethrate:.8f}")

        # === Function 'ethusdrate' ===
        def ethusdrate(*_):
            """
            Converts the entered USD value to its ETH equivalent using the current ETH/USD rate.
            Triggered whenever the USD input field is modified. If the input is invalid or non-numeric,
            it clears the ETH field. This function ensures real-time synchronization between both fields.

            Parameters:
            - *_: Placeholder for trace callback arguments (unused).

            Returns:
            - None
            """
            try:
                usd = float(usdvar.get())
                eth = usd / ethrate
                ethvar.set(f"{eth:.8f}")
            except ValueError:
                ethvar.set("")

        usdvar.trace_add("write", ethusdrate)

        # === Function 'itemlabel' ===
        def itemlabel(parent, labeltext, var, readonly=False):
            """
            Creates a labeled input field within the specified parent container. The field label is placed above
            a styled Tkinter Entry widget, which can be optionally set to read-only mode. This utility function
            is used throughout forms to generate consistent input blocks for deposit details.

            Parameters:
            - parent (tk.Widget): The container in which to place the label and entry.
            - labeltext (str): The descriptive text shown above the input field.
            - var (tk.StringVar): The StringVar bound to the entry field for real-time value access.
            - readonly (bool): If True, the input will be set to read-only mode. Defaults to False.

            Returns:
            - tk.Entry: The configured entry widget instance.
            """
            tk.Label(parent, text=labeltext, anchor="w", bg=self.bg, fg=self.fg, font=("Arial", 11)).pack(fill="x", pady=(0, 5))
            state: Literal["normal", "disabled", "readonly"] = "readonly" if readonly else "normal"
            entry = tk.Entry(parent, bd=0, bg=self.card, readonlybackground=self.card, fg=self.fg, font=("Arial", 11), highlightbackground="#757575", highlightcolor="#757575", highlightthickness=1, insertbackground=self.fg, textvariable=var, state=state)
            entry.pack(fill="x", pady=(0, 15), ipady=6)
            return entry

        itemlabel(inner, "Inject in USD", usdvar)
        itemlabel(inner, "Inject in ETH", ethvar, readonly=True)
        tk.Label(inner, text="Priority", anchor="w", bg=self.bg, fg=self.fg, font=("Arial", 11)).pack(fill="x", pady=(0, 5))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.TCombobox", fieldbackground=self.card, background=self.card, foreground=self.fg, borderwidth=1, relief="flat")
        style.map("Custom.TCombobox", fieldbackground=[("readonly", self.card)], background=[("readonly", self.card)], foreground=[("readonly", self.fg)])

        readonly_state: Literal["readonly"] = "readonly"
        prioritymenu = ttk.Combobox(inner, textvariable=priorityvar, values=[pool["basename"], pool["quotename"]], state=readonly_state, style="Custom.TCombobox")
        prioritymenu.pack(fill="x", pady=(0, 15), ipady=5)

        itemlabel(inner, "Bull Timing", bullvar)
        itemlabel(inner, "Bear Timing", bearvar)

        # === Function 'pushstacked' ===
        def pushstacked():
            """
            Validates the deposit form, checks for required mnemonic configuration, and parses input values.
            If valid, the function clears the form and shows a confirmation summary. It then saves the deposit
            to the local database and prepares for execution. Errors in configuration or input are handled
            with alerts. This is the primary entry point for confirming a new liquidity stack.

            Parameters:
            - None

            Returns:
            - None
            """
            mnemonic = None
            try:
                with open(PATHCONFIGFILE, "r") as f:
                    settings = json.load(f)
                    mnemonic = settings.get("mnemonic", "").strip()
            except (FileNotFoundError, json.JSONDecodeError):
                messagebox.showerror("Missing Mnemonic", "Mnemonic is required.\nFile 'config/settings.json' not found or unreadable.")
                popup.destroy()
                return

            if not mnemonic:
                messagebox.showerror("Missing Mnemonic", "Mnemonic is required but missing from config/settings.json.")
                popup.destroy()
                return

            ethvalue = ethvar.get().strip()
            usdvalue = usdvar.get().strip()

            if not ethvalue or not usdvalue or not pool:
                return

            try:
                usdfloat = float(usdvalue)
                ethfloat = float(ethvalue)
            except ValueError:
                return

            for child in outer.winfo_children():
                child.destroy()

            confirmation = tk.Frame(outer, bg=self.bg)
            confirmation.pack(expand=True, fill="both", padx=20, pady=20)
            popup.geometry("400x640")
            wallet = EthereumWallet(mnemonic)

            # === Function 'pushfields' ===
            def pushfields(title, value):
                """
                Renders a labeled field for confirmation display during the stacking process.
                It includes a bold title label and a plain value label, followed by a horizontal divider.
                Used to summarize deposit details like token addresses, priority, and bull/bear timings.

                Parameters:
                - title (str): The label/title of the field (e.g., "Wallet").
                - value (str): The corresponding value to display (e.g., wallet address).

                Returns:
                - None
                """
                tk.Label(confirmation, text=title, bg=self.bg, fg=self.fg, font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
                tk.Label(confirmation, text=value, bg=self.bg, fg=self.fg, font=("Arial", 11), anchor="w", justify="left", wraplength=400).pack(anchor="w", pady=(0, 5))
                tk.Frame(confirmation, height=1, bg=self.border).pack(fill="x", padx=0, pady=8)

            pushfields("Wallet", wallet.publickey())
            pushfields("Base Token", pool["baseaddr"])
            pushfields("Quote Token", pool["quoteaddr"])
            pushfields("Deposit", f"USD: {usdfloat:.4f}\nETH: {ethfloat:.10f}")
            pushfields("Priority", priorityvar.get())
            pushfields("Bull Timing", f"{bullvar.get()} seconds")
            pushfields("Bear Timing", f"{bearvar.get()} seconds")
            buttons = tk.Frame(confirmation, bg=self.bg)
            buttons.pack(fill="x", pady=(10, 5))

            # === Function 'pushexecute' ===
            def pushexecute():
                """
                Clears the confirmation view and starts a simulated stacking progress with a loading bar.
                After a delay, it calls `pushfinalize` to display the result based on the registration status.
                Ensures the user sees visual feedback and that the stacking UI flow continues smoothly.

                Parameters:
                - None

                Returns:
                - None
                """
                for item in confirmation.winfo_children():
                    item.destroy()

                popup.geometry("400x150")
                stackinglabel = tk.Label(confirmation, bg=self.bg, fg=self.fg, font=("Arial", 11, "italic"), text="Stacking liquidity, please wait")
                stackinglabel.pack(pady=(20, 10))
                progress = ttk.Progressbar(confirmation, mode="indeterminate", length=180)
                progress.pack(pady=10)
                progress.start(10)

                # === Function 'pushfinalize' ===
                def pushfinalize(action):
                    """
                    Finalizes the stacking operation by stopping the progress bar and displaying the result message.
                    It checks whether the application is registered and shows appropriate feedback.
                    Also triggers a refresh of the stacked section and renders a button to close the popup.

                    Parameters:
                    - action (bool): Indicates whether to proceed with completion logic. Must be True to finalize.

                    Returns:
                    - None
                    """
                    if action is True:
                        progress.stop()
                        progress.destroy()
                        stackinglabel.destroy()

                        if self.checkregistration():
                            tk.Label(
                                confirmation, text="Application not registered\nLiquidity not sent to network",
                                fg="red", bg=self.bg, font=("Arial", 14)
                            ).pack(pady=(10, 15))
                        else:
                            tk.Label(
                                confirmation, text="Deposit completed", fg="green", bg=self.bg,
                                font=("Arial", 16, "bold")
                            ).pack(pady=(10, 15))

                    tk.Frame(confirmation, height=1, bg=self.border).pack(fill="x", padx=0, pady=(8, 25))
                    self.after(1000, self.refreshstacked, True)

                    tk.Button(confirmation, command=popup.destroy, activebackground="#3f8b0f", activeforeground="#ffffff", bd=0, bg="#52a022", fg="#ffffff", font=("Arial", 9), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=14, pady=6, relief="flat", text="Close Prompt").pack()
                    popup.geometry("400x190")

                self.after(5000, pushfinalize, True)

            tk.Button(buttons, bg="#52a022", command=pushexecute, fg="#ffffff", font=("Arial", 10), padx=10, pady=6, relief="flat", text="Confirm").pack(side="left", expand=True, fill="x", padx=(0, 5))
            tk.Button(buttons, bg="#c03434", command=popup.destroy, fg="#ffffff", font=("Arial", 10), padx=10, pady=6, relief="flat", text="Cancel").pack(side="left", expand=True, fill="x", padx=(5, 0))

            try:
                addentry = LiquidityLogs(
                    pairs=pool["pairs"], basename=pool["basename"], quotename=pool["quotename"],
                    network=pool["network"], chainid=pool["chainid"], type=pool["type"], baseaddr=pool["baseaddr"],
                    baselogo=pool["baselogo"], basebalance=pool["basebalance"], basefees=pool["basefees"],
                    baseprice=pool["baseprice"], quoteaddr=pool["quoteaddr"], quotelogo=pool["quotelogo"],
                    quotebalance=pool["quotebalance"], quotefees=pool["quotefees"], quoteprice=pool["quoteprice"],
                    tvl=pool["tvl"], volume=pool["volume"], apr=pool["apr"], group=pool["group"], fiat=pool["fiat"],
                    factory=pool["factory"], url=pool["url"], stacked=ethfloat, status=True, priority=priorityvar.get(),
                    bull=bullvar.get(), bear=bearvar.get()
                )

                self.dbsession.add(addentry)
                self.dbsession.commit()
            except Exception as e:
                messagebox.showerror("Database Error", str(e))
                popup.destroy()

        tk.Button(inner, activebackground="#6e1c2b", activeforeground="#ffffff", bd=0, bg="#c03434", command=pushstacked, fg="#ffffff", font=("Arial", 11), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=10, pady=8, text="Submit", relief="flat").pack(fill="x", pady=(0, 5), ipady=0)

    # === Function 'chainslist' ===
    def chainslist(self):
        """
        Creates and returns a button widget used to toggle the network selection list.
        Styled consistently with the app's theme. Clicking this button triggers `networktoogle()`
        to show or hide the dropdown with available blockchain networks.

        Parameters:
        - None

        Returns:
        - tk.Button: The network toggle button labeled “All Chains ▼”.
        """
        return tk.Button(self.filterleft, activebackground="#353535", activeforeground=self.fg, bd=0, bg="#454545", command=self.networktoogle, fg=self.fg, font=("Arial", 9), padx=14, pady=8, relief="flat", text="All Chains ▼")

    # === Function 'popupsettings' ===
    def popupsettings(self):
        """
        Displays a popup window allowing the user to configure or update app settings, including
        serial registration code, wallet address, and mnemonic. Reads existing settings if available,
        and stores changes to the configuration file upon submission. Also triggers a registration check.

        Parameters:
        - None

        Returns:
        - None
        """
        popup, outer = self.popuploader("Settings", 500, 380)
        outer.config(padx=20, pady=20)

        serialvalue = tk.StringVar()
        walletvalue = tk.StringVar()
        mnemonicstring = tk.StringVar()

        if os.path.exists(self.confapps):
            try:
                with open(self.confapps, "r") as f:
                    saved = json.load(f)
                    serialvalue.set(saved.get("serial", ""))
                    walletvalue.set(saved.get("wallet", ""))
                    mnemonicstring.set(saved.get("mnemonic", ""))
            except (json.JSONDecodeError, OSError):
                pass

        # === Function 'itemlabel' ===
        def itemlabel(labeltext, var):
            """
            Creates a labeled input field specifically for the settings popup interface.
            Places a label above a styled Entry widget linked to a StringVar, using consistent theme colors.
            This helper ensures uniform input appearance and spacing throughout the configuration form.

            Parameters:
            - labeltext (str): The label text displayed above the entry field.
            - var (tk.StringVar): The variable bound to the entry widget for value storage and retrieval.

            Returns:
            - tk.Entry: The configured entry widget instance.
            """
            tk.Label(outer, text=labeltext, anchor="w", bg=self.bg, fg=self.fg, font=("Arial", 10)).pack(fill="x", pady=(0, 5))
            entry = tk.Entry(outer, bd=0, bg=self.card, fg=self.fg, highlightbackground="#757575", highlightcolor="#757575", highlightthickness=1, insertbackground=self.fg, textvariable=var, font=("Arial", 11))

            entry.pack(fill="x", pady=(0, 5), ipady=5)
            tk.Frame(outer, height=10, bg=self.bg).pack(fill="x")
            return entry

        itemlabel("Serial Code", serialvalue)
        itemlabel("Wallet ETH", walletvalue)
        tk.Label(outer, text="Wallet Mnemonic", anchor="w", bg=self.bg, fg=self.fg, font=("Arial", 10)).pack(fill="x", pady=(0, 5))
        mnemonicbox = tk.Text(outer, bd=0, highlightbackground="#757575", highlightcolor="#757575", highlightthickness=1, insertbackground=self.fg, bg=self.card, fg=self.fg, font=("Arial", 11), height=5, wrap="word")
        mnemonicbox.insert("1.0", mnemonicstring.get())
        mnemonicbox.pack(fill="both", expand=True, pady=(0, 10))

        # === Function 'storeconf' ===
        def storeconf():
            """
            Saves the user's registration serial, Ethereum wallet address, and mnemonic phrase
            from the settings popup into the local configuration file. Ensures the configuration
            directory exists before writing, and triggers a UI update to reflect the new registration status.
            Closes the popup upon successful save.

            Parameters:
            - None

            Returns:
            - None
            """
            data = {
                "serial": serialvalue.get(), "wallet": walletvalue.get(),
                "mnemonic": mnemonicbox.get("1.0", "end").strip()
            }

            os.makedirs(PATHCONFIG, exist_ok=True)
            with open(self.confapps, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            popup.destroy()
            self.registrationstatus()

        tk.Frame(outer, height=10, bg=self.bg).pack(fill="x")
        tk.Button(outer, activebackground="#6e1c2b", activeforeground="#ffffff", bd=0, bg="#c03434", fg="#ffffff", font=("Arial", 11), highlightbackground="#ffffff", highlightcolor="#ffffff", highlightthickness=1, padx=10, pady=8, relief="flat", text="Submit", command=storeconf).pack(fill="x", pady=(0, 5), ipady=0)

    # === Function 'destroclear' ===
    def destroclear(self, attr_name):
        """
        Destroys a UI section if it exists and clears the reference by setting it to None.
        This utility is used to remove view fragments (like stacked or pool sections) when switching views.

        Parameters:
        - attr_name (str): The attribute name of the section to destroy (e.g., "sectionaero").

        Returns:
        - None
        """
        section = getattr(self, attr_name, None)
        if section:
            section.destroy()
        setattr(self, attr_name, None)

    # === Function 'appfilters' ===
    def appfilters(self):
        """
        Resets and re-initializes all filter buttons depending on the current protocol mode.
        If protocol is 'Velodrome', also restores the network dropdown.
        Adds search filters and re-binds the reset button. Used before showing the liquidity view.

        Parameters:
        - None

        Returns:
        - None
        """
        for widget in self.filterleft.winfo_children():
            widget.destroy()

        if self.protocolvars.get() == "Velodrome":
            self.buttonnetwork = tk.Button(self.filterleft, activebackground="#353535", activeforeground=self.fg, bd=0, bg="#454545", command=self.networktoogle, fg=self.fg, font=("Arial", 9), padx=14, pady=8, relief="flat", text="All Chains ▼")
            self.buttonnetwork.pack(side="left", padx=4, pady=2)

        self.addsearchfilters()
        self.resetsearchfilters()

    # === Function 'showliquidity' ===
    def showliquidity(self):
        """
        Switches the main interface view to display Velodrome liquidity pools.
        Destroys the stacked section if present, resets filters, and renders
        the scrollable Velodrome pool list. Used when the "Liquidity" button is clicked.

        Parameters:
        - None

        Returns:
        - None
        """
        self.hideallwrappers()
        self.appfilters()

        if self.sectionaero:
            self.sectionaero.destroy()
            self.sectionaero = None

        self.sectionvelo = self.blockvelodrome()
        self.sectionvelo.pack(fill="both", expand=True)

    # === Function 'showstacked' ===
    def showstacked(self):
        """
        Switches the main view to show the user's stacked and unstacked liquidity deposits.
        Destroys other view sections and initializes the stacked block, including filter buttons
        for Stacked, Unstacked, and Reset. Handles errors gracefully if loading fails.

        Parameters:
        - None

        Returns:
        - None
        """
        self.stopscrollloop()
        self.hideallwrappers()
        self.destroclear("sectionaero")

        try:
            self.sectionaero = self.blockstacked()
        except Exception as e:
            print(f"[ERROR] Failed to create blockstacked: {e}")
            self.sectionaero = None
            return

        if self.sectionaero and self.sectionaero.winfo_exists():
            self.sectionaero.pack(fill="both", expand=True)

    # === Function 'refreshstacked' ===
    def refreshstacked(self, action):
        """
        Rebuilds the 'stacked' section to reflect any recent changes, such as new deposits or unstack actions.
        Ensures any previous scroll loops are canceled and clears the view before loading a fresh stacked block.
        Optionally makes the stacked section visible depending on the `action` parameter.

        Parameters:
        - action (bool): If True, displays the section after reloading.

        Returns:
        - None
        """
        self.stopscrollloop()
        self.destroclear("sectionaero")

        try:
            self.sectionaero = self.blockstacked()
        except Exception as e:
            print(f"[ERROR] Failed to create blockstacked: {e}")
            self.sectionaero = None
            return

        if self.sectionvelo and self.sectionvelo.winfo_exists() and self.sectionvelo.winfo_ismapped():
            self.sectionvelo.pack_forget()

        if action is True and self.sectionaero and self.sectionaero.winfo_exists():
            self.sectionaero.pack(fill="both", expand=True)

    # === Function 'unstackdeposit' ===
    def unstackdeposit(self, pool):
        """
        Marks a given liquidity pool entry as unstacked in the database.
        Updates the `status` field of the pool to False, commits the change,
        refreshes the UI to reflect the updated status, and displays a confirmation message.

        Parameters:
        - pool (LiquidityLogs): The liquidity log object representing the deposit to unstack.

        Returns:
        - None
        """
        try:
            pool.status = False
            self.dbsession.commit()
            self.refreshstacked(True)
            messagebox.showinfo("Unstacked", f"{pool.pairs} has been unstacked.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unstack: {e}")

    # === Function 'hideallwrappers' ===
    def hideallwrappers(self):
        """
        Hides all primary content wrapper sections from the GUI.
        This is used when switching between major views (e.g., liquidity vs stacked).
        Only performs UI hiding (not deletion) so that views can be reused later.

        Parameters:
        - None

        Returns:
        - None
        """
        for section in [self.sectionvelo, self.sectionaero]:
            if section is not None:
                section.pack_forget()


# === Callback ===
if __name__ == "__main__":
    """
    Entry point for the application. This block checks whether a data sync is needed 
    before launching the main GUI. If an update is required, it starts a synchronization 
    popup and then launches the interface. Otherwise, it directly opens the application window.

    Parameters:
    - None

    Returns:
    - None
    """
    # === Function 'startgui' ===
    def startgui():
        """
        Initializes and launches the main GUI application.
        Creates an instance of the ThemedApp class and starts its Tkinter main loop.
        Used as a callback after synchronization or as the direct launch routine.

        Parameters:
        - None

        Returns:
        - None
        """
        print("[INFO] Starting the GUI")
        app = ThemedApp()
        app.mainloop()

    checker = SyncHandler(sqlitepath=PATHDATA, maxseconds=3600)
    if checker.checkupdate():
        print("[INFO] Synchronization update")
        syncpopup = SyncPopup(hookcallback=startgui, datapath=PATHDATA)
        syncpopup.syncstart()
    else:
        startgui()
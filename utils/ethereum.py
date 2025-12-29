# === Import packages ===
from bip32utils import BIP32_HARDEN
from bip32utils import BIP32Key
from eth_account import Account
from mnemonic import Mnemonic
from web3 import Web3


# === Class 'EthereumWallet' ===
class EthereumWallet:
    """
    This class provides a complete implementation of an Ethereum wallet based on BIP-44 hierarchical deterministic paths.
    It supports seed generation from mnemonic phrases, private/public key derivation, and ETH balance retrieval from the blockchain.
    The wallet uses standard derivation paths compatible with Ethereum and supports custom RPC endpoints for balance checking.
    It is designed for developers building blockchain apps, wallets, or tools requiring on-the-fly address/key management.

    Parameters:
    - mnemonic (str): A BIP-39 compatible mnemonic phrase used to generate the wallet seed.
    - passphrase (str): An optional BIP-39 passphrase to further secure the seed (default is an empty string).

    Returns:
    - None
    """

    # === Function '__init__' ===
    def __init__(self, mnemonic: str, passphrase: str = ""):
        """
        Initializes the EthereumWallet instance by generating the seed from the provided mnemonic and optional passphrase.
        This seed is used later for BIP-44 path derivation to generate Ethereum-compatible private keys and addresses.
        It uses the English word list from the `mnemonic` library to ensure compatibility with commonly used wallets.

        Parameters:
        - mnemonic (str): A BIP-39 mnemonic phrase that serves as the root for key derivation.
        - passphrase (str): An optional string that adds entropy to the seed. Default is "".

        Returns:
        - None
        """
        self.mnemonic = mnemonic
        self.seed = Mnemonic("english").to_seed(mnemonic, passphrase)

    # === Function 'derivebip44' ===
    def derivebip44(self, path: str = "m/44'/60'/0'/0/0") -> bytes:
        """
        Derives the private key along a specified BIP-44 path using the wallet's seed.
        By default, it targets the Ethereum derivation path `m/44'/60'/0'/0/0` for the first account.
        It supports both hardened and non-hardened derivation levels and allows custom derivation paths if needed.

        Parameters:
        - path (str): A BIP-44 compliant derivation path (default is the first Ethereum account path).

        Returns:
        - bytes: The derived private key in raw byte format.
        """
        bip32_root_key_obj = BIP32Key.fromEntropy(self.seed)
        for level in path.split("/")[1:]:
            hardened = False
            if level.endswith("'"):
                hardened = True
                level = level[:-1]
            index = int(level)
            if hardened:
                index += BIP32_HARDEN
            bip32_root_key_obj = bip32_root_key_obj.ChildKey(index)

        return bip32_root_key_obj.PrivateKey()

    # === Function 'privatekey' ===
    def privatekey(self) -> str:
        """
        Extracts and returns the private key corresponding to the default BIP-44 Ethereum derivation path.
        The private key is returned as a hexadecimal string, suitable for importing into wallet software or signing tools.
        It prints a log message to indicate the operation being performed for traceability.

        Parameters:
        - None

        Returns:
        - str: The derived private key represented as a hex-encoded string.
        """
        print("[INFO] Extracting private key")
        privkey = self.derivebip44()
        return privkey.hex()

    # === Function 'publickey' ===
    def publickey(self) -> str:
        """
        Extracts and returns the Ethereum public wallet address derived from the private key using the default path.
        Internally, it uses the `eth_account` library to compute the public address from the private key.
        This method helps retrieve a usable address for transactions, balance checks, or wallet integrations.

        Parameters:
        - None

        Returns:
        - str: The Ethereum public address corresponding to the derived private key.
        """
        print("[INFO] Extracting public wallet address")
        pubkey = self.derivebip44()
        acct = Account.from_key(pubkey)
        return acct.address

    # === Function 'balance' ===
    def balance(self, rpc="https://eth.llamarpc.com") -> float:
        """
        Connects to the specified Ethereum RPC endpoint and fetches the current Ether balance of the derived public address.
        It defaults to a public RPC node if none is provided. The balance is returned in Ether (ETH), not Wei.
        If the operation fails due to a network error or invalid address, it logs the error and returns 0.0 ETH.

        Parameters:
        - rpc (str): A string representing the RPC URL to query Ethereum balances. Defaults to 'https://eth.llamarpc.com'.

        Returns:
        - float: The current Ether balance of the wallet's public address, expressed in ETH. Returns 0.0 on failure.
        """
        try:
            address = Web3.to_checksum_address(self.publickey())
            w3 = Web3(Web3.HTTPProvider(rpc))
            balance_wei = w3.eth.get_balance(address)
            return w3.from_wei(balance_wei, 'ether')
        except Exception as e:
            print(f"[ERROR] Could not fetch ETH balance: {e}")
            return 0.0
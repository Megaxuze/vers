import requests
from web3 import Web3
from eth_account import Account
import time
import sys
import os
import random
from decimal import Decimal

# Import data_hex dan private_keys jika diperlukan
# Pastikan file data_hex.py dan privateKeys.py ada di direktori yang sama dengan script ini
from data_hex import Data_HEX
from privateKeys import private_keys, VALUE_ETH, GAS_LIMIT_ADJUSTMENT, FEE_GWEI

# Define network details
networks = {
    'InitVerse': {
        'rpc_url': 'https://rpc-testnet.iniscan.com',
        'chain_id': 233,
        'contract_address': '0x7BEf93022D48b9df745B77D0Fd348fB415b026e2'  # Alamat Router ObsSwap
    }
}

# Token contract addresses
tokens = {
    'USDT': '0x36AA81a7aEeAB8f09e154d3E779Bb81beA54501A',
    'INI': '0x9e66cd15226464EFBa8b7B2847A0880AFC236c5C',
    'TOKEN': '0xcF259Bca0315C6D32e877793B6a10e97e7647FdE'
}

# ABI minimal untuk ERC20 dan Router (sesuaikan dengan ABI sebenarnya)
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "type": "function"
    }
]

# Contoh ABI minimal untuk Router (swapExactTokensForTokens)
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def print_banner():
    banner_text = """
\033[96m=========================================================
                        INITVERSE | AIRDROP ASC
=========================================================
                  Credit By       : Airdrop ASC
                  Telegram Channel: @airdropasc
                  Telegram Group  : @autosultan_group
=========================================================\033[0m
    """
    print(banner_text)

# Fungsi untuk mengambil address dari private key
def get_address_from_private_key(private_key):
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    account = Account.from_key(private_key)
    return account.address

# Fungsi untuk memanggil API user info
def get_user_info(address):
    url = f"https://candyapi.inichain.com/airdrop/v1/user/userInfo?address={address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        user_info = response.json()
        print("User Info:", user_info)
        return user_info
    except requests.RequestException as e:
        print(f"Failed to get user info: {e}")
        return None

# Fungsi untuk memanggil API User Task Status
def get_user_task_status(address):
    url = f"https://candyapi.inichain.com/airdrop/v1/user/UserTaskStatus?address={address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        task_status = response.json()
        print("User Task Status:", task_status)
        return task_status
    except requests.RequestException as e:
        print(f"Failed to get user task status: {e}")
        return None

# Fungsi untuk memanggil API Get Authorization URL
def get_authorization_url(address):
    url = f"https://candyapi.inichain.com/airdrop/v1/discord/getAuthorizationUrl?address={address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Debug: Cetak isi respons sebelum parsing
        print("Authorization URL Response:", response.text)
        
        try:
            response_json = response.json()
            # Karena 'data' adalah string URL, langsung ambil 'data'
            authorization_url = response_json.get('data')
            if authorization_url:
                print("Authorization URL:", authorization_url)
                return authorization_url
            else:
                print("Authorization URL not found in response.")
                return None
        except ValueError:
            # Jika response tidak bisa di-parse sebagai JSON
            print("Response is not in JSON format.")
            return None

    except requests.RequestException as e:
        print(f"Failed to get authorization URL: {e}")
        return None

# Fungsi untuk memvalidasi private key
def validate_private_key(private_key):
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    if len(private_key) != 66:
        return None
    try:
        Account.from_key(private_key)
        return private_key
    except ValueError:
        return None

# Fungsi untuk memeriksa verifikasi sebelum swap
def verify_user_before_swap(private_key):
    address = get_address_from_private_key(private_key)
    print(f"Address: {address}")

    # Panggil API untuk mendapatkan informasi pengguna dan status task
    user_info = get_user_info(address)
    if not user_info:
        print("\033[91mCannot retrieve user info. Exiting.\033[0m")
        sys.exit(1)

    task_status = get_user_task_status(address)
    if not task_status:
        print("\033[91mCannot retrieve task status. Exiting.\033[0m")
        sys.exit(1)

    # Cek apakah task 'Swap Any Token on Obs Swap' tersedia
    daily_tasks = task_status.get('data', {}).get('dailyTaskInfo', [])
    if not daily_tasks:
        print("\033[91mNo daily tasks found. Exiting.\033[0m")
        return False

    # Identifikasi task 'Swap Any Token on Obs Swap'
    # Berdasarkan data yang diberikan, kita lihat ada dua dailyTaskInfo
    # Pertama dengan 'flag': True dan 'completeDays': 1
    # Kedua dengan 'flag': False dan 'count': 10
    # Asumsikan task pertama adalah 'Swap Any Token on Obs Swap'
    swap_task = daily_tasks[0]
    if swap_task.get('flag'):
        print("\033[92mSwap task is available. Proceeding...\033[0m")
        authorization_url = get_authorization_url(address)
        if authorization_url:
            print(f"Please authorize the swap via this URL: {authorization_url}")
            # Prompt user to authorize manually
            input("After authorization is complete, press Enter to continue...")
            # Anda bisa menambahkan verifikasi tambahan di sini jika API menyediakan
            # Misalnya, memeriksa kembali status task setelah otorisasi
            # Namun, tanpa browser automation, otorisasi harus dilakukan secara manual
            return True
        else:
            print("\033[91mAuthorization URL not available. Cannot proceed.\033[0m")
            return False
    else:
        print("\033[91mSwap task is not available. Exiting.\033[0m")
        return False

# Fungsi untuk mendapatkan jumlah swap berdasarkan jenis swap
def get_swap_amount(swap_type):
    swap_amounts = {
        "INI to TOKEN": 0.01,
        "INI to USDT": 0.01,
        "USDT to INI": 0.006,
        "TOKEN to INI": 0.006
    }
    return swap_amounts.get(swap_type, 0)

# Fungsi untuk mengirim transaksi approve
def approve_token(web3, account, token_address, spender_address, amount):
    try:
        # ABI minimal untuk ERC20 approve
        token_contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        nonce = web3.eth.get_transaction_count(account.address)

        txn = token_contract.functions.approve(spender_address, amount).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 150000,  # Gas limit untuk approve
            'gasPrice': web3.to_wei(FEE_GWEI, 'gwei')
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=account.key)
        # Sesuaikan akses atribut raw_transaction berdasarkan versi Web3.py
        raw_txn = signed_txn.raw_transaction if hasattr(signed_txn, 'raw_transaction') else signed_txn.rawTransaction
        tx_hash = web3.eth.send_raw_transaction(raw_txn)
        print(f"\033[92mApproval Tx Hash: {web3.to_hex(tx_hash)}\033[0m")
        return web3.to_hex(tx_hash)
    except Exception as e:
        print(f"\033[91mError approving token: {e}\033[0m")
        return None

# Fungsi untuk mengirim transaksi swap menggunakan ABI Router
def send_swap_transaction(web3, account, router_contract, amount_in, amount_out_min, path, to, deadline):
    try:
        nonce = web3.eth.get_transaction_count(account.address)
        txn = router_contract.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            path,
            to,
            deadline
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 200000,  # Sesuaikan gas limit sesuai kebutuhan
            'gasPrice': web3.to_wei(FEE_GWEI, 'gwei')
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=account.key)
        # Sesuaikan akses atribut raw_transaction berdasarkan versi Web3.py
        raw_txn = signed_txn.raw_transaction if hasattr(signed_txn, 'raw_transaction') else signed_txn.rawTransaction
        tx_hash = web3.eth.send_raw_transaction(raw_txn)
        print(f"\033[92mSwap Tx Hash: {web3.to_hex(tx_hash)}\033[0m")
        return web3.to_hex(tx_hash)
    except ValueError as e:
        print(f"\033[91mError sending swap transaction: {e}\033[0m")
        return None
    except Exception as e:
        print(f"\033[91mUnexpected error sending swap transaction: {e}\033[0m")
        return None

# Fungsi untuk membuat folder transaksi
def create_tx_folder():
    base_folder = 'Tx_Hash'
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    return base_folder

# Fungsi untuk membuat folder jaringan
def create_network_folder(base_folder, network_name):
    network_folder = os.path.join(base_folder, network_name.replace(' ', '-'))
    if not os.path.exists(network_folder):
        os.makedirs(network_folder)
    return network_folder

# Fungsi untuk membuat file swap
def create_swap_file(network_folder, swap_name):
    swap_file_path = os.path.join(network_folder, f'Tx_{swap_name.replace(" ", "-")}.txt')
    if not os.path.exists(swap_file_path):
        open(swap_file_path, 'w').close()  
    return swap_file_path

# Fungsi untuk menyimpan hash transaksi
def save_tx_hash(tx_hash, source_network, swap_name):
    base_folder = create_tx_folder()
    source_folder = create_network_folder(base_folder, source_network)
    swap_file_path = create_swap_file(source_folder, swap_name)
    with open(swap_file_path, 'a') as file:
        file.write(f'{tx_hash}\n')

# Fungsi untuk menjalankan swap network
def run_swap_network(web3, account, swap_count, active_swaps):
    print(f"\nRunning \033[96m{swap_count}\033[0m swaps for active networks")
    total_success = 0

    # Inisialisasi kontrak Router
    router_contract = web3.eth.contract(address=Web3.to_checksum_address(networks['InitVerse']['contract_address']), abi=ROUTER_ABI)

    for _ in range(swap_count):
        for swap, active in active_swaps.items():
            if not active:
                continue  # Skip inactive swaps

            try:
                # Tetapkan nilai sesuai swap type
                if swap in ["INI to TOKEN", "INI to USDT"]:
                    input_token = 'INI'
                    output_token = swap.split(' to ')[1]
                    amount_in = get_swap_amount(swap)
                    amount_in_wei = Web3.to_wei(amount_in, 'ether')
                    amount_out_min = 0  # Sesuaikan sesuai kebutuhan, bisa menggunakan slippage
                    path = [tokens[input_token], tokens[output_token]]
                    to = account.address
                    deadline = int(time.time()) + 600  # 10 menit dari sekarang
                    display_amount = f"{amount_in:.4f} {input_token}"
                elif swap in ["USDT to INI", "TOKEN to INI"]:
                    input_token = swap.split(' to ')[0]
                    output_token = 'INI'
                    amount_in = get_swap_amount(swap)
                    amount_in_wei = Web3.to_wei(amount_in, 'ether')
                    amount_out_min = 0  # Sesuaikan sesuai kebutuhan, bisa menggunakan slippage
                    path = [tokens[input_token], tokens[output_token]]
                    to = account.address
                    deadline = int(time.time()) + 600  # 10 menit dari sekarang
                    display_amount = f"{amount_in:.4f} {input_token}"
                else:
                    print(f"\033[91mUnknown swap type: {swap}. Skipping...\033[0m")
                    continue

                # Pastikan kontrak token dikenal
                token_address = tokens.get(input_token)
                if not token_address:
                    print(f"\033[91mUnknown input token: {input_token}. Skipping...\033[0m")
                    continue

                # Inisialisasi kontrak token
                token_contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)

                # Cek allowance
                current_allowance = token_contract.functions.allowance(account.address, networks['InitVerse']['contract_address']).call()
                required_allowance = amount_in_wei

                if current_allowance < required_allowance:
                    print(f"\033[93mApproving {input_token} for swap...\033[0m")
                    approval_tx_hash = approve_token(web3, account, token_address, networks['InitVerse']['contract_address'], required_allowance)
                    if approval_tx_hash:
                        print(f"\033[92mApproval Transaction Sent: {approval_tx_hash}\033[0m")
                        # Tunggu hingga transaksi approval selesai
                        receipt = web3.eth.wait_for_transaction_receipt(approval_tx_hash, timeout=300)
                        if receipt.status == 1:
                            print(f"\033[92mApproval Transaction Confirmed: {approval_tx_hash}\033[0m")
                        else:
                            print(f"\033[91mApproval Transaction Failed: {approval_tx_hash}\033[0m")
                            continue
                    else:
                        print(f"\033[91mFailed to approve {input_token}. Skipping swap.\033[0m")
                        continue

                # Kirim transaksi swap
                swap_tx_hash = send_swap_transaction(web3, account, router_contract, amount_in_wei, amount_out_min, path, to, deadline)
                if swap_tx_hash:
                    print(f"\033[92mSwap Tx Hash: {swap_tx_hash}\nSwap: {swap} | Amount: {display_amount}\033[0m")
                    save_tx_hash(swap_tx_hash, 'InitVerse', swap)
                    total_success += 1

                # Waktu tunggu acak antara 11-12 menit
                wait_time = random.uniform(660, 720)  
                for remaining in range(int(wait_time), 0, -1):
                    sys.stdout.write(f"\rWaiting for next swap: {remaining} seconds remaining.")
                    sys.stdout.flush()
                    time.sleep(1)

            except KeyboardInterrupt:
                print("\n\033[93mBot Stop\033[0m")
                sys.exit(0)
            except Exception as e:
                print(f"\033[91mError processing {swap}: {e}\033[0m")

    print(f"\n\n\033[92mAll Swaps Complete: Total {total_success}\033[0m")

# Fungsi utama
def main():
    os.system('clear') if os.name == 'posix' else os.system('cls')  
    print_banner()

    print("    \033[96m=== Main Menu ===\033[0m")
    print("    1. InitVerse")
    print("    2. Run Swap Network")
    print("    \033[96m==================\033[0m\n")

    network_choice = input("    \033[96mNetwork choice (1-2): \033[0m")

    if network_choice == "1":
        print("\033[94mWhat the hell are you looking for? Get the hell out of here -_-\033[0m")
        sys.exit(0)

    elif network_choice == "2":
        active_swaps = {
            "INI to TOKEN": True,
            "INI to USDT": True,
            "USDT to INI": True,
            "TOKEN to INI": True
        }

        while True:
            os.system('clear')  
            print_banner()  
            print("\n\033[96m    Select Swaps to Disable \033[0m")
            for idx, (swap, active) in enumerate(active_swaps.items(), start=1):
                status = "\033[92mActive\033[0m" if active else "\033[91mInactive\033[0m"
                print(f"    {idx}. {swap} [{status}]")
            print(f"    {len(active_swaps) + 1}. Run Swap")

            choice = input(f"    \033[96mSelect swap to toggle (1-{len(active_swaps)}) or {len(active_swaps)+1} to run swap: \033[0m")

            if choice.isdigit():
                choice = int(choice)
                if 1 <= choice <= len(active_swaps):
                    swap_name = list(active_swaps.keys())[choice - 1]
                    active_swaps[swap_name] = not active_swaps[swap_name]
                elif choice == len(active_swaps) + 1:
                    break  
                else:
                    print("\033[91mInvalid choice. Please try again.\033[0m")
                    time.sleep(1)
            else:
                print("\033[91mInvalid input. Please enter a number.\033[0m")
                time.sleep(1)

        os.system('clear')  
        print_banner()

        try:
            swap_count = int(input("\033[96mHow many times to make Transactions: \033[0m"))
        except ValueError:
            print("\033[91mInvalid input. Please enter a valid number.\033[0m")
            sys.exit(1)

        private_key = validate_private_key(private_keys[0])
        if not private_key:
            print("\033[91mInvalid private key format.\033[0m")
            sys.exit(1)
        account = Account.from_key(private_key)

        # Verifikasi sebelum swap
        verification_result = verify_user_before_swap(private_key)
        if not verification_result:
            print("\033[91mVerification failed. Exiting.\033[0m")
            sys.exit(1)

        os.system('clear')  
        print_banner()
        run_swap_network(Web3(Web3.HTTPProvider(networks['InitVerse']['rpc_url'])), account, swap_count, active_swaps)

if __name__ == "__main__":
    main()

import os

def read_file(filename):
    try:
        with open(filename, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using default value.")
        return None

def load_config():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return {
        'CLIENT_ID': read_file(os.path.join(root_dir, 'client_id.txt')),
        'ACCESS_TOKEN': read_file(os.path.join(root_dir, 'access_token.txt')),
        'PAPER_TRADING': True,
        'PAPER_TRADING_BALANCE': 100000,
        'PRIMARY_TIMEFRAME': '5',
        'SECONDARY_TIMEFRAME': '15',
        'RISK_REWARD_RATIO': 2,
        'CANDLES_TO_ANALYZE': 10
    }
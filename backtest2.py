import pandas as pd
import numpy as np
from fyers_apiv3 import fyersModel
from datetime import datetime, timedelta
import time

# Configuration
CLIENT_ID = open("client_id.txt", 'r').read().strip()
ACCESS_TOKEN = open("access_token.txt", 'r').read().strip()
SYMBOLS = ["NSE:ADANIENT-EQ", "NSE:ADANIPORTS-EQ", "NSE:APOLLOHOSP-EQ", "NSE:ASIANPAINT-EQ", "NSE:AXISBANK-EQ",
        "NSE:BAJAJ-AUTO-EQ", "NSE:BAJFINANCE-EQ", "NSE:BAJAJFINSV-EQ", "NSE:BPCL-EQ", "NSE:BHARTIARTL-EQ",
        # "NSE:BRITANNIA-EQ", "NSE:CIPLA-EQ", "NSE:COALINDIA-EQ", "NSE:DIVISLAB-EQ", "NSE:DRREDDY-EQ",
        # "NSE:EICHERMOT-EQ", "NSE:GRASIM-EQ", "NSE:HCLTECH-EQ", "NSE:HDFCBANK-EQ", "NSE:HDFCLIFE-EQ",
        # "NSE:HEROMOTOCO-EQ", "NSE:HINDALCO-EQ", "NSE:HINDUNILVR-EQ", "NSE:ICICIBANK-EQ", "NSE:INDUSINDBK-EQ",
        # "NSE:INFY-EQ", "NSE:ITC-EQ", "NSE:JSWSTEEL-EQ", "NSE:KOTAKBANK-EQ", "NSE:LT-EQ",
        # "NSE:M&M-EQ", "NSE:MARUTI-EQ", "NSE:NESTLEIND-EQ", "NSE:NTPC-EQ", "NSE:ONGC-EQ",
        # "NSE:POWERGRID-EQ", "NSE:RELIANCE-EQ", "NSE:SBILIFE-EQ", "NSE:SBIN-EQ", "NSE:SUNPHARMA-EQ",
        "NSE:TCS-EQ", "NSE:TATACONSUM-EQ", "NSE:TATAMOTORS-EQ", "NSE:TATASTEEL-EQ", "NSE:TECHM-EQ",
        "NSE:TITAN-EQ", "NSE:ULTRACEMCO-EQ", "NSE:UPL-EQ", "NSE:WIPRO-EQ"]  # Add more symbols as needed
START_DATE = datetime(2024, 1, 10)
END_DATE = datetime(2024, 9, 13)
TIMEFRAME = "D"  # Daily timeframe

# Initialize FYERS API
fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, log_path="")

def get_historical_data(symbol, start_date, end_date, timeframe):
    data = {
        "symbol": symbol,
        "resolution": timeframe,
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }
    response = fyers.history(data)
    if response['s'] == 'ok':
        df = pd.DataFrame(response['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        return df
    else:
        print(f"Error fetching data for {symbol}: {response['message']}")
        return None

def calculate_indicators(df):
    df['200_MA'] = df['close'].rolling(window=200).mean()
    df['20_MA'] = df['close'].rolling(window=20).mean()
    df['RSI'] = calculate_rsi(df['close'], 14)
    df['ATR'] = calculate_atr(df, 14)
    return df

def calculate_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def identify_breakout(df):
    df['resistance'] = df['high'].rolling(window=20).max()
    df['support'] = df['low'].rolling(window=20).min()
    df['breakout_long'] = (df['close'] > df['resistance'].shift(1)) & (df['volume'] > df['volume'].rolling(window=20).mean())
    df['breakout_short'] = (df['close'] < df['support'].shift(1)) & (df['volume'] > df['volume'].rolling(window=20).mean())
    return df

def backtest_strategy(df):
    position = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []

    for i in range(1, len(df)):
        current_price = df['close'].iloc[i]
        
        if position == 0:
            if df['breakout_long'].iloc[i] and df['close'].iloc[i] > df['200_MA'].iloc[i] and df['RSI'].iloc[i] < 70:
                position = 1
                entry_price = current_price
                stop_loss = entry_price - 2 * df['ATR'].iloc[i]
                take_profit = entry_price + 4 * df['ATR'].iloc[i]
                trades.append({'entry_date': df.index[i], 'type': 'long', 'entry_price': entry_price})
            elif df['breakout_short'].iloc[i] and df['close'].iloc[i] < df['200_MA'].iloc[i] and df['RSI'].iloc[i] > 30:
                position = -1
                entry_price = current_price
                stop_loss = entry_price + 2 * df['ATR'].iloc[i]
                take_profit = entry_price - 4 * df['ATR'].iloc[i]
                trades.append({'entry_date': df.index[i], 'type': 'short', 'entry_price': entry_price})
        
        elif position == 1:
            if current_price <= stop_loss or current_price >= take_profit:
                trades[-1]['exit_date'] = df.index[i]
                trades[-1]['exit_price'] = current_price
                trades[-1]['pnl'] = (current_price - entry_price) / entry_price
                position = 0
        
        elif position == -1:
            if current_price >= stop_loss or current_price <= take_profit:
                trades[-1]['exit_date'] = df.index[i]
                trades[-1]['exit_price'] = current_price
                trades[-1]['pnl'] = (entry_price - current_price) / entry_price
                position = 0

    # Close any open position at the end of the backtest
    if position != 0:
        trades[-1]['exit_date'] = df.index[-1]
        trades[-1]['exit_price'] = df['close'].iloc[-1]
        if position == 1:
            trades[-1]['pnl'] = (df['close'].iloc[-1] - entry_price) / entry_price
        else:
            trades[-1]['pnl'] = (entry_price - df['close'].iloc[-1]) / entry_price

    return trades

def run_backtest():
    all_trades = []
    for symbol in SYMBOLS:
        print(f"Backtesting {symbol}")
        df = get_historical_data(symbol, START_DATE, END_DATE, TIMEFRAME)
        if df is not None and len(df) > 200:
            df = calculate_indicators(df)
            df = identify_breakout(df)
            trades = backtest_strategy(df)
            for trade in trades:
                trade['symbol'] = symbol
            all_trades.extend(trades)
        time.sleep(1)  # To avoid hitting API rate limits

    if not all_trades:
        print("\nNo trades were executed during the backtest period.")
        return pd.DataFrame()

    results_df = pd.DataFrame(all_trades)
    
    if 'pnl' not in results_df.columns:
        print("\nNo completed trades in the backtest.")
        return results_df

    total_trades = len(results_df)
    winning_trades = len(results_df[results_df['pnl'] > 0])
    total_return = results_df['pnl'].sum()
    
    print(f"\nBacktest Results:")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {winning_trades}")
    print(f"Win Rate: {winning_trades / total_trades:.2%}")
    print(f"Total Return: {total_return:.2%}")
    
    return results_df

if __name__ == "__main__":
    results = run_backtest()
    if not results.empty:
        results.to_csv("backtest_results.csv", index=False)
    else:
        print("No results to save.")

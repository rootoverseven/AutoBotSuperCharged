import pandas as pd
import numpy as np
from fyers_apiv3 import fyersModel
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

# Configuration variables
PRIMARY_TIMEFRAME = "5"  # 5-minute candles
SECONDARY_TIMEFRAME = "15"  # 15-minute candles for confirmation
CANDLES_TO_ANALYZE = 10  # Number of candles to analyze for patterns
RISK_REWARD_RATIO = 2  # Fixed 1:2 risk-reward ratio
STARTING_CAPITAL = 100000  # Starting capital of 100,000 (adjust as needed)

# Load API credentials and initialize Fyers API
client_id = open("client_id.txt", 'r').read().strip()
access_token = open("access_token.txt", 'r').read().strip()
fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")

def get_nifty50_symbols():
    return [
        "NSE:ADANIENT-EQ", "NSE:ADANIPORTS-EQ", "NSE:APOLLOHOSP-EQ", "NSE:ASIANPAINT-EQ", "NSE:AXISBANK-EQ",
        "NSE:BAJAJ-AUTO-EQ", "NSE:BAJFINANCE-EQ", "NSE:BAJAJFINSV-EQ", "NSE:BPCL-EQ", "NSE:BHARTIARTL-EQ",
        "NSE:BRITANNIA-EQ", "NSE:CIPLA-EQ", "NSE:COALINDIA-EQ", "NSE:DIVISLAB-EQ", "NSE:DRREDDY-EQ",
        "NSE:EICHERMOT-EQ", "NSE:GRASIM-EQ", "NSE:HCLTECH-EQ", "NSE:HDFCBANK-EQ", "NSE:HDFCLIFE-EQ",
        "NSE:HEROMOTOCO-EQ", "NSE:HINDALCO-EQ", "NSE:HINDUNILVR-EQ", "NSE:ICICIBANK-EQ", "NSE:INDUSINDBK-EQ",
        "NSE:INFY-EQ", "NSE:ITC-EQ", "NSE:JSWSTEEL-EQ", "NSE:KOTAKBANK-EQ", "NSE:LT-EQ",
        "NSE:M&M-EQ", "NSE:MARUTI-EQ", "NSE:NESTLEIND-EQ", "NSE:NTPC-EQ", "NSE:ONGC-EQ",
        "NSE:POWERGRID-EQ", "NSE:RELIANCE-EQ", "NSE:SBILIFE-EQ", "NSE:SBIN-EQ", "NSE:SUNPHARMA-EQ",
        "NSE:TCS-EQ", "NSE:TATACONSUM-EQ", "NSE:TATAMOTORS-EQ", "NSE:TATASTEEL-EQ", "NSE:TECHM-EQ",
        "NSE:TITAN-EQ", "NSE:ULTRACEMCO-EQ", "NSE:UPL-EQ", "NSE:WIPRO-EQ"
    ]

def get_historical_data(symbol, interval, start_date, end_date):
    data = {
        "symbol": symbol,
        "resolution": interval,
        "date_format": "1",
        "range_from": start_date,
        "range_to": end_date,
        "cont_flag": "1"
    }
    try:
        response = fyers.history(data=data)
        if 'candles' in response:
            df = pd.DataFrame(response['candles'], columns=["timestamp", "open", "high", "low", "close", "volume"])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
    return pd.DataFrame()

def analyze_price_action(data):
    if len(data) < CANDLES_TO_ANALYZE:
        return {"price_score": 0, "trend": "neutral", "volatility": 0}

    price_score = 0
    candle_sizes = []

    for i in range(-CANDLES_TO_ANALYZE, 0):
        candle = data.iloc[i]
        next_candle = data.iloc[i+1] if i+1 < 0 else None
        candle_size = abs(candle['close'] - candle['open'])
        candle_sizes.append(candle_size)

        # Bullish candle
        if candle['close'] > candle['open']:
            price_score += 1
        # Bearish candle
        elif candle['close'] < candle['open']:
            price_score -= 1

        # Long lower wick (potential reversal)
        if (min(candle['open'], candle['close']) - candle['low']) > (0.5 * abs(candle['close'] - candle['open'])):
            price_score += 1 if candle['close'] > candle['open'] else -1

        # Long upper wick (potential reversal)
        if (candle['high'] - max(candle['open'], candle['close'])) > (0.5 * abs(candle['close'] - candle['open'])):
            price_score -= 1 if candle['close'] > candle['open'] else 1

        # Engulfing patterns
        if next_candle is not None:
            # Bullish engulfing
            if candle['close'] < candle['open'] and next_candle['close'] > next_candle['open'] and \
               next_candle['close'] > candle['open'] and next_candle['open'] < candle['close']:
                price_score += 2
            # Bearish engulfing
            elif candle['close'] > candle['open'] and next_candle['close'] < next_candle['open'] and \
                 next_candle['close'] < candle['open'] and next_candle['open'] > candle['close']:
                price_score -= 2

    # Trend analysis
    short_term_price = data['close'].iloc[-5:].mean()
    long_term_price = data['close'].iloc[-20:].mean()

    if short_term_price > long_term_price:
        price_score += 2
        trend = "uptrend"
    elif short_term_price < long_term_price:
        price_score -= 2
        trend = "downtrend"
    else:
        trend = "neutral"

    # Volatility calculation
    volatility = np.std(candle_sizes) / np.mean(candle_sizes)

    return {"price_score": price_score, "trend": trend, "volatility": volatility}

def analyze_volume(data):
    if len(data) < CANDLES_TO_ANALYZE:
        return 0

    avg_volume = data['volume'].rolling(window=CANDLES_TO_ANALYZE).mean()
    current_volume = data['volume'].iloc[-1]

    volume_ratio = current_volume / avg_volume.iloc[-1]

    if volume_ratio > 1.5:
        return 2  # Significantly higher volume
    elif volume_ratio > 1.2:
        return 1  # Higher volume
    elif volume_ratio < 0.8:
        return -1  # Lower volume
    elif volume_ratio < 0.5:
        return -2  # Significantly lower volume
    else:
        return 0  # Average volume

def calculate_atr(data, period=14):
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean().iloc[-1]

def analyze_timeframe(data, interval):
    if len(data) < CANDLES_TO_ANALYZE:
        return None

    price_analysis = analyze_price_action(data.tail(CANDLES_TO_ANALYZE))
    volume_score = analyze_volume(data.tail(CANDLES_TO_ANALYZE))
    total_score = price_analysis['price_score'] + volume_score

    return {
        'score': total_score,
        'trend': price_analysis['trend'],
        'atr': calculate_atr(data),
        'last_close': data['close'].iloc[-1],
        'last_high': data['high'].iloc[-1],
        'last_low': data['low'].iloc[-1]
    }

def select_best_stock(nifty_trend, stocks_data):
    stock_scores = []

    for symbol, data in stocks_data.items():
        analysis_primary = analyze_timeframe(data[PRIMARY_TIMEFRAME], PRIMARY_TIMEFRAME)
        analysis_secondary = analyze_timeframe(data[SECONDARY_TIMEFRAME], SECONDARY_TIMEFRAME)

        if analysis_primary is None or analysis_secondary is None:
            continue

        total_score = analysis_primary['score'] + analysis_secondary['score']

        if nifty_trend == "downtrend":
            if total_score < 0:  # Select stocks with negative scores for short trades in downtrend
                stock_scores.append((symbol, abs(total_score), analysis_primary['trend'], analysis_primary['atr'], "short"))
        else:  # uptrend
            if total_score > 0:  # Select stocks with positive scores for long trades in uptrend
                stock_scores.append((symbol, total_score, analysis_primary['trend'], analysis_primary['atr'], "long"))

    stock_scores.sort(key=lambda x: x[1], reverse=True)

    return stock_scores[0] if stock_scores else None

def calculate_quantity(current_price, available_capital):
    usable_balance = available_capital * 0.95
    scaling_factor = usable_balance / 4000

    if current_price <= 500:
        base_quantity = 25
    elif 500 < current_price <= 1500:
        base_quantity = 20
    elif 1500 < current_price <= 3000:
        base_quantity = 6
    else:
        base_quantity = 1

    scaled_quantity = int(base_quantity * scaling_factor)
    max_affordable = int(usable_balance / current_price)
    final_quantity = min(scaled_quantity, max_affordable)

    return max(1, final_quantity)

def backtest_strategy(start_date, end_date, starting_capital):
    nifty_data = get_historical_data("NSE:NIFTY50-INDEX", PRIMARY_TIMEFRAME, start_date, end_date)
    
    symbols = get_nifty50_symbols()
    stocks_data = {symbol: {
        PRIMARY_TIMEFRAME: get_historical_data(symbol, PRIMARY_TIMEFRAME, start_date, end_date),
        SECONDARY_TIMEFRAME: get_historical_data(symbol, SECONDARY_TIMEFRAME, start_date, end_date)
    } for symbol in symbols}

    trades = []
    current_capital = starting_capital
    position = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    symbol = None
    entry_time = None
    shares = 0

    for timestamp in nifty_data.index:
        if position == 0:
            # Determine Nifty trend
            nifty_trend = "uptrend" if nifty_data['close'].loc[:timestamp].iloc[-1] > nifty_data['close'].loc[:timestamp].iloc[-10] else "downtrend"
            
            # Select best stock based on Nifty trend
            current_stocks_data = {s: {tf: data.loc[:timestamp] for tf, data in stock_data.items()} for s, stock_data in stocks_data.items()}
            best_stock = select_best_stock(nifty_trend, current_stocks_data)
            
            if best_stock:
                symbol, _, _, atr, trade_type = best_stock
                current_price = stocks_data[symbol][PRIMARY_TIMEFRAME].loc[timestamp, 'close']
                
                # Calculate quantity based on the new logic
                shares = calculate_quantity(current_price, current_capital)
                
                if trade_type == "long":
                    entry_price = current_price
                    stop_loss = entry_price - atr
                    take_profit = entry_price + (atr * RISK_REWARD_RATIO)
                    position = 1
                    entry_time = timestamp
                elif trade_type == "short":
                    entry_price = current_price
                    stop_loss = entry_price + atr
                    take_profit = entry_price - (atr * RISK_REWARD_RATIO)
                    position = -1
                    entry_time = timestamp
        
        else:
            current_price = stocks_data[symbol][PRIMARY_TIMEFRAME].loc[timestamp, 'close']
            
            if position == 1:
                if current_price <= stop_loss or current_price >= take_profit:
                    exit_price = stop_loss if current_price <= stop_loss else take_profit
                    pnl = (exit_price - entry_price) * shares
                    current_capital += pnl
                    trades.append({
                        'symbol': symbol,
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position': 'long',
                        'quantity': shares,
                        'result': 'loss' if exit_price == stop_loss else 'profit',
                        'pnl': pnl,
                        'capital_after_trade': current_capital
                    })
                    position = 0
            elif position == -1:
                if current_price >= stop_loss or current_price <= take_profit:
                    exit_price = stop_loss if current_price >= stop_loss else take_profit
                    pnl = (entry_price - exit_price) * shares
                    current_capital += pnl
                    trades.append({
                        'symbol': symbol,
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position': 'short',
                        'quantity': shares,
                        'result': 'loss' if exit_price == stop_loss else 'profit',
                        'pnl': pnl,
                        'capital_after_trade': current_capital
                    })
                    position = 0

    return trades, current_capital

def analyze_backtest_results(trades, starting_capital, ending_capital):
    if not trades:
        return "No trades executed during the backtest period.", None, None

    df = pd.DataFrame(trades)
    
    total_trades = len(df)
    winning_trades = len(df[df['result'] == 'profit'])
    losing_trades = len(df[df['result'] == 'loss'])
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    total_pnl = df['pnl'].sum()
    max_drawdown = (df['capital_after_trade'].cummax() - df['capital_after_trade']).max()
    roi = (ending_capital - starting_capital) / starting_capital * 100

    results = f"""
    Backtest Results:
    -----------------
    Starting Capital: {starting_capital:.2f}
    Ending Capital: {ending_capital:.2f}
    Return on Investment: {roi:.2f}%
    Total Trades: {total_trades}
    Winning Trades: {winning_trades}
    Losing Trades: {losing_trades}
    Win Rate: {win_rate:.2f}%
    Total P/L: {total_pnl:.2f}
    Max Drawdown: {max_drawdown:.2f}
    """

    # Ensure the result folder exists
    ensure_result_folder_exists()

    # Plot cumulative P/L
    plt.figure(figsize=(12, 6))
    plt.plot(df['exit_time'], df['capital_after_trade'])
    plt.title('Account Balance Over Time')
    plt.xlabel('Date')
    plt.ylabel('Account Balance')
    plt.grid(True)
    
    # Save the chart
    chart_filename = 'result/account_balance_over_time.png'
    plt.savefig(chart_filename)
    plt.close()

    # Save trade details
    trade_details_filename = save_trade_details(trades, starting_capital)

    return results, chart_filename, trade_details_filename

def ensure_result_folder_exists():
    if not os.path.exists('results'):
        os.makedirs('results')

def save_trade_details(trades, starting_capital):
    filename = 'results/trade_details.txt'
    with open(filename, 'w') as f:
        f.write(f"Trade Details (Starting Capital: {starting_capital:.2f}):\n")
        f.write("=" * 50 + "\n\n")
        for trade in trades:
            f.write(f"Symbol: {trade['symbol']}\n")
            f.write(f"Entry Time: {trade['entry_time']}\n")
            f.write(f"Exit Time: {trade['exit_time']}\n")
            f.write(f"Position: {trade['position']}\n")
            f.write(f"Quantity: {trade['quantity']}\n")
            f.write(f"Entry Price: {trade['entry_price']:.2f}\n")
            f.write(f"Exit Price: {trade['exit_price']:.2f}\n")
            f.write(f"Result: {trade['result']}\n")
            f.write(f"P/L: {trade['pnl']:.2f}\n")
            f.write(f"Capital After Trade: {trade['capital_after_trade']:.2f}\n")
            f.write("\n" + "-" * 30 + "\n\n")
    return filename

def main():
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # Backtest for the last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')

    print(f"Backtesting from {start_date} to {end_date}...")
    trades, ending_capital = backtest_strategy(start_date, end_date, STARTING_CAPITAL)
    
    if trades:
        results, chart_filename, trade_details_filename = analyze_backtest_results(trades, STARTING_CAPITAL, ending_capital)
        print(results)
        print(f"Account balance chart saved as '{chart_filename}'")
        print(f"Trade details saved as '{trade_details_filename}'")
    else:
        print("No trades were executed during the backtest period.")

if __name__ == "__main__":
    main()
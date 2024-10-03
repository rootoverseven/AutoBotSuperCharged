import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from fyers_apiv3 import fyersModel

# Configuration variables
PRIMARY_TIMEFRAME = 5  # 5-minute candles
SECONDARY_TIMEFRAME = 15  # 15-minute candles for confirmation
CANDLES_TO_ANALYZE = 10  # Number of candles to analyze for patterns
RISK_REWARD_RATIO = 2  # Fixed 1:2 risk-reward ratio
TOTAL_CAPITAL = 10000
TRADABLE_AMMOUNT = 5000

# Load API credentials
client_id = open("client_id.txt", 'r').read().strip()
access_token = open("access_token.txt", 'r').read().strip()

# Initialize Fyers API
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

def download_historical_data(symbol, start_date, end_date, interval):
    data = {
        "symbol": symbol if symbol.startswith("NSE:") else f"NSE:{symbol}-EQ",
        "resolution": str(interval),
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }

    try:
        response = fyers.history(data)
        if response['s'] == 'ok':
            df = pd.DataFrame(response['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            df['timestamp'] = df['timestamp'].dt.tz_localize(None)
            df.set_index('timestamp', inplace=True)
            return df
        else:
            print(f"Error fetching data for {symbol}: {response['message']}")
            return None
    except Exception as e:
        print(f"Exception while fetching data for {symbol}: {str(e)}")
        return None

def download_and_save_data(symbols, start_date, end_date):
    os.makedirs("historical_data", exist_ok=True)
    for symbol in symbols:
        print(f"Downloading data for {symbol}")
        df_5min = download_historical_data(symbol, start_date, end_date, PRIMARY_TIMEFRAME)
        if df_5min is not None:
            df_5min.to_csv(f"historical_data/{symbol}_5min.csv")
        
        df_15min = download_historical_data(symbol, start_date, end_date, SECONDARY_TIMEFRAME)
        if df_15min is not None:
            df_15min.to_csv(f"historical_data/{symbol}_15min.csv")

def get_historical_data(symbol, interval, days, currentDate):
    end_date = currentDate
    # Adjust end_date to the start of the current candle
    start_date = end_date - timedelta(days=days)
    
    # Read data from CSV
    filename = f"historical_data/{symbol}_{interval}min.csv"
    df = pd.read_csv(filename, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Filter data for the specified date range
    mask = (df.index >= start_date) & (df.index < end_date)
    df = df.loc[mask]
    # df = df.loc[mask].iloc[:-1]  # Exclude the last candle
    
    return df

def analyze_price_action(data):
    if len(data) < CANDLES_TO_ANALYZE:
        return {"price_score": 0, "trend": "neutral", "volatility": 0}

    recent_candles = data.iloc[-CANDLES_TO_ANALYZE:]
    price_score = 0
    candle_sizes = []

    for i in range(CANDLES_TO_ANALYZE - 1):
        current_candle = recent_candles.iloc[i]
        next_candle = recent_candles.iloc[i+1] if i+1 < CANDLES_TO_ANALYZE else None
        candle_size = abs(current_candle['close'] - current_candle['open'])
        candle_sizes.append(candle_size)

        if current_candle['close'] > current_candle['open']:
            price_score += 1
        elif current_candle['close'] < current_candle['open']:
            price_score -= 1

        if (min(current_candle['open'], current_candle['close']) - current_candle['low']) > (0.5 * abs(current_candle['close'] - current_candle['open'])):
            price_score += 1 if current_candle['close'] > current_candle['open'] else -1

        if (current_candle['high'] - max(current_candle['open'], current_candle['close'])) > (0.5 * abs(current_candle['close'] - current_candle['open'])):
            price_score -= 1 if current_candle['close'] > current_candle['open'] else 1

        if next_candle is not None:
            if current_candle['close'] < current_candle['open'] and next_candle['close'] > next_candle['open'] and \
               next_candle['close'] > current_candle['open'] and next_candle['open'] < current_candle['close']:
                price_score += 2
            elif current_candle['close'] > current_candle['open'] and next_candle['close'] < next_candle['open'] and \
                 next_candle['close'] < current_candle['open'] and next_candle['open'] > current_candle['close']:
                price_score -= 2

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

    volatility = np.std(candle_sizes) / np.mean(candle_sizes)

    return {"price_score": price_score, "trend": trend, "volatility": volatility}

def analyze_volume(data):
    if len(data) < CANDLES_TO_ANALYZE:
        return 0

    avg_volume = data['volume'].rolling(window=CANDLES_TO_ANALYZE).mean()
    current_volume = data['volume'].iloc[-1]

    # print(f"avg vol:{avg_volume.iloc[-1]}")
    # print(f"cur vol:{current_volume}")

    volume_ratio = current_volume / avg_volume.iloc[-1]

    if volume_ratio > 1.5:
        return 2
    elif volume_ratio > 1.2:
        return 1
    elif volume_ratio < 0.8:
        return -1
    elif volume_ratio < 0.5:
        return -2
    else:
        return 0

def calculate_atr(data, period=14):
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean().iloc[-1]

def analyze_timeframe(symbol, interval, current_date):
    data = get_historical_data(symbol, interval, 5, current_date)
    if data.empty:
        print(f"No data available for {symbol} on {interval} timeframe")
        return None
    
    # Ensure we have enough data for analysis
    if len(data) < CANDLES_TO_ANALYZE:
        print(f"Insufficient data for {symbol} on {interval} timeframe. Got {len(data)} candles, need {CANDLES_TO_ANALYZE}.")
        return None
    
    price_analysis = analyze_price_action(data)
    # print(f"analysing volumen for symbol: {symbol}")
    volume_score = analyze_volume(data)
    total_score = price_analysis['price_score'] + volume_score

    last_completed_candle = data.iloc[-1]

    return {
        'score': total_score,
        'trend': price_analysis['trend'],
        'atr': calculate_atr(data),
        'last_close': last_completed_candle['close'],
        'last_high': last_completed_candle['high'],
        'last_low': last_completed_candle['low'],
        'timestamp': last_completed_candle.name
    }

def select_best_stock(nifty_trend, current_date):
    stock_scores = []

    for symbol in nifty50_symbols:
        analysis_primary = analyze_timeframe(symbol, PRIMARY_TIMEFRAME, current_date)
        analysis_secondary = analyze_timeframe(symbol, SECONDARY_TIMEFRAME, current_date)

        if analysis_primary is None or analysis_secondary is None:
            continue

        total_score = analysis_primary['score'] + analysis_secondary['score']
        print(f"Stock: {symbol}, Primary Score: {analysis_primary['score']}, Secondary Score: {analysis_secondary['score']}, Total Score: {total_score}")

        if nifty_trend == "downtrend":
            if total_score < 0:
                stock_scores.append((symbol, abs(total_score), analysis_primary['trend'], analysis_primary['atr'], "short"))
        else:  # uptrend
            if total_score > 0:
                stock_scores.append((symbol, total_score, analysis_primary['trend'], analysis_primary['atr'], "long"))

    stock_scores.sort(key=lambda x: x[1], reverse=True)
    return stock_scores[0] if stock_scores else None

def is_market_open(current_time):
    return (current_time.time() >= datetime.strptime("09:15", "%H:%M").time() and 
            current_time.time() < datetime.strptime("15:30", "%H:%M").time() and
            current_time.weekday() < 5)  # Monday is 0, Friday is 4

def run_backtest(start_date, end_date):
    total_capital = TOTAL_CAPITAL
    quantity_bought = None
    charges = None
    absolute_profit = None
    net_profit = None
    trades = []
    open_trade = None
    current_high = None
    global nifty50_symbols
    nifty50_symbols = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL",
        "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
        "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
        "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
        "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
        "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA",
        "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM",
        "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
    ]

    current_date = start_date
    while current_date <= end_date:
        if not is_market_open(current_date):
            current_date += timedelta(minutes=5)
            continue

        print(f"\nProcessing {current_date}")

        # Analyze NIFTY50 trend
        nifty_data = get_historical_data("NIFTY50", PRIMARY_TIMEFRAME, 1, current_date)
        if nifty_data.empty:
            print("Failed to fetch Nifty 50 data. Retrying in 5 seconds.")
            current_date += timedelta(minutes=5)
            continue

        if len(nifty_data) >= 10:
            nifty_trend = "uptrend" if nifty_data['close'].iloc[-1] > nifty_data['close'].iloc[-10] else "downtrend"
        else:
            print("Not enough data to determine Nifty trend. Skipping this iteration.")
            current_date += timedelta(minutes=5)
            continue
        print(f"Nifty 50 is currently in a {nifty_trend}.")

        # skip short trades
        if (nifty_trend == "downtrend"):
            current_date += timedelta(minutes=5)
            continue

        if open_trade is None:
            if current_date.time() < datetime.strptime("10:30", "%H:%M").time() or current_date.time() > datetime.strptime("15:00", "%H:%M").time():
                print("Out of trade time")
                current_date += timedelta(minutes=5)
                continue
            best_stock = select_best_stock(nifty_trend, current_date)
            if not best_stock:
                print("No suitable stocks found for trading. Retrying in 30 seconds.")
                current_date += timedelta(minutes=5)
                continue

            symbol, total_score, trend, atr, trade_type = best_stock
            print(f"Best stock for trading: {symbol} with Total Score: {total_score:.2f}, Trend: {trend}, ATR: {atr:.2f}, Trade Type: {trade_type}")
            current_price = analyze_timeframe(symbol, PRIMARY_TIMEFRAME, current_date)['last_close']
             
            absolute_profit = 0
            absolute_loss = 0
            entry_price = current_price
            quantity_bought = TRADABLE_AMMOUNT // (entry_price/5)
            if trade_type == "long":
                stop_loss = round(entry_price - atr, 2)
                take_profit = round(entry_price + (atr * RISK_REWARD_RATIO), 2)
                absolute_profit = quantity_bought * (take_profit - entry_price)
                absolute_loss = quantity_bought * (stop_loss - entry_price)
            else:  # short
                stop_loss = round(entry_price + atr, 2)
                take_profit = round(entry_price - (atr * RISK_REWARD_RATIO), 2)
                absolute_profit = quantity_bought * (entry_price - take_profit)
                absolute_loss = quantity_bought * (entry_price - stop_loss)
            
            charges = quantity_bought * (take_profit * 0.00066 + entry_price * 0.00044)
            
            net_profit = absolute_profit - charges
            net_loss = absolute_loss - charges
            trade_ammount = quantity_bought * entry_price / 5
            if (net_profit<=0 or net_profit<= 1.2*abs(net_loss)):
                current_date += timedelta(minutes=5)
                continue

            open_trade = {
                'symbol': symbol,
                'entry_time': current_date,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'trade_type': trade_type,

            }
            # if current_high > take_profit:

            print(f"Entered {trade_type} trade for {symbol} at {entry_price:.2f}. SL: {stop_loss:.2f}, Target: {take_profit:.2f}")
        
        elif open_trade:
            print(f"Order ongoing")
            current_price = analyze_timeframe(open_trade['symbol'], PRIMARY_TIMEFRAME, current_date)['last_close']
            current_high = analyze_timeframe(symbol, PRIMARY_TIMEFRAME, current_date)['last_high']
            current_low = analyze_timeframe(symbol, PRIMARY_TIMEFRAME, current_date)['last_low']
            if (open_trade['trade_type'] == 'long' and (current_price <= open_trade['stop_loss'] or current_low <= open_trade['stop_loss'])) or \
                (open_trade['trade_type'] == 'short' and (current_price >= open_trade['stop_loss'] or current_high >= open_trade['stop_loss'])):
                pnl = (open_trade['stop_loss'] - open_trade['entry_price']) if open_trade['trade_type'] == 'long' else (open_trade['entry_price'] - open_trade['stop_loss'])
                absolute_profit = quantity_bought * pnl
                net_profit = absolute_profit - charges
                
                trades.append({
                    'symbol': open_trade['symbol'],
                    'entry_time': open_trade['entry_time'],
                    'exit_time': current_date,
                    'entry_price': open_trade['entry_price'],
                    'exit_price': open_trade['stop_loss'],
                    'pnl': pnl,
                    'trade_type': open_trade['trade_type'],
                    'exit_reason': 'stop_loss',
                    'total_capital': total_capital,
                    'tradable_ammount': TRADABLE_AMMOUNT,
                    'quantity_bought': quantity_bought,
                    'trade_ammount' : trade_ammount,
                    'absolute_profit': absolute_profit,
                    'exit_ammount': trade_ammount + absolute_profit,
                    'charges': charges,
                    'net_profit': net_profit
                })
                total_capital = total_capital + net_profit
                print(f"Exited {open_trade['trade_type']} trade for {open_trade['symbol']} at stop loss. PNL: {pnl:.2f}")
                open_trade = None
            elif (open_trade['trade_type'] == 'long' and (current_price >= open_trade['take_profit'] or current_high >= open_trade['take_profit'])) or \
                 (open_trade['trade_type'] == 'short' and (current_price <= open_trade['take_profit'] or current_low <= open_trade['take_profit'])):
                pnl = (open_trade['take_profit'] - open_trade['entry_price']) if open_trade['trade_type'] == 'long' else (open_trade['entry_price'] - open_trade['take_profit'])
                absolute_profit = quantity_bought * pnl
                net_profit = absolute_profit - charges
                trades.append({
                    'symbol': open_trade['symbol'],
                    'entry_time': open_trade['entry_time'],
                    'exit_time': current_date,
                    'entry_price': open_trade['entry_price'],
                    'exit_price': current_price,
                    'pnl': pnl,
                    'trade_type': open_trade['trade_type'],
                    'exit_reason': 'take_profit',
                    'total_capital': total_capital,
                    'tradable_ammount': TRADABLE_AMMOUNT,
                    'quantity_bought': quantity_bought,
                    'trade_ammount' : trade_ammount,
                    'absolute_profit': absolute_profit,
                    'exit_ammount': trade_ammount + absolute_profit,
                    'charges': charges,
                    'net_profit': net_profit
                })
                total_capital = total_capital + net_profit
                print(f"Exited {open_trade['trade_type']} trade for {open_trade['symbol']} at take profit. PNL: {pnl:.2f}")
                open_trade = None

        # Close any open trade at market close
        if current_date.time() >= datetime.strptime("15:25", "%H:%M").time() and open_trade:
            last_candle = current_date - timedelta(minutes=5)
            current_price = analyze_timeframe(open_trade['symbol'], PRIMARY_TIMEFRAME, last_candle)['last_close']
            pnl = (current_price - open_trade['entry_price']) if open_trade['trade_type'] == 'long' else (open_trade['entry_price'] - current_price)
            absolute_profit = quantity_bought * pnl
            net_profit = absolute_profit - charges            
            trades.append({
                'symbol': open_trade['symbol'],
                'entry_time': open_trade['entry_time'],
                'exit_time': current_date,
                'entry_price': open_trade['entry_price'],
                'exit_price': current_price,
                'pnl': pnl,
                'trade_type': open_trade['trade_type'],
                'exit_reason': 'market_close',
                'total_capital': total_capital,
                'tradable_ammount': TRADABLE_AMMOUNT,
                'quantity_bought': quantity_bought,
                'trade_ammount' : trade_ammount,
                'absolute_profit': absolute_profit,
                'exit_ammount': trade_ammount + absolute_profit,
                'charges': charges,
                'net_profit': net_profit
            })
            total_capital = total_capital + net_profit
            print(f"Closed trade for {open_trade['symbol']} at market close. PNL: {pnl:.2f}")
            open_trade = None
        # if current_high > open_trade['take']
        current_date += timedelta(minutes=5)

    print("Backtest completed.")
    return pd.DataFrame(trades)

# Main execution
if __name__ == "__main__":
    start_date = datetime(2024, 7, 1, 15, 30)
    end_date = datetime(2024, 9, 13, 15, 40)

    print(start_date)

    nifty50_symbols = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL",
        "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
        "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
        "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
        "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
        "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA",
        "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM",
        "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
    ]

    # Download and save historical data
    download_and_save_data(nifty50_symbols, start_date - timedelta(days=5), end_date)
    
    # Handle NIFTY50 separately
    nifty_symbol = "NSE:NIFTY50-INDEX"
    print(f"Downloading data for {nifty_symbol}")
    df_5min = download_historical_data(nifty_symbol, start_date - timedelta(days=5), end_date, PRIMARY_TIMEFRAME)
    if df_5min is not None:
        df_5min.to_csv(f"historical_data/NIFTY50_5min.csv")
    
    df_15min = download_historical_data(nifty_symbol, start_date - timedelta(days=5), end_date, SECONDARY_TIMEFRAME)
    if df_15min is not None:
        df_15min.to_csv(f"historical_data/NIFTY50_15min.csv")

    print("Data downloaded and saved.")

    results = run_backtest(start_date, end_date)

    if not results.empty:
        total_pnl = results['pnl'].sum()
        win_rate = (results['pnl'] > 0).mean()
        total_trades = len(results)
        profitable_trades = (results['pnl'] > 0).sum()
        loss_making_trades = (results['pnl'] < 0).sum()

        print("\nBacktest Summary:")
        print(f"Total Trades: {total_trades}")
        print(f"Profitable Trades: {profitable_trades}")
        print(f"Loss-making Trades: {loss_making_trades}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Total PNL: {total_pnl:.2f}")

        # Calculate Sharpe Ratio
        risk_free_rate = 0.05  # Assume 5% annual risk-free rate
        daily_returns = results.groupby(results['exit_time'].dt.date)['pnl'].sum()
        sharpe_ratio = (daily_returns.mean() - risk_free_rate / 252) / (daily_returns.std() * np.sqrt(252))
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")

        # Calculate Maximum Drawdown
        cumulative_returns = (1 + daily_returns).cumprod()
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = drawdown.min()
        print(f"Maximum Drawdown: {max_drawdown:.2%}")

        # Save results to CSV
        results.to_csv('backtest_results.csv', index=False)
    else:
        print("No trades were executed during the backtest period.")
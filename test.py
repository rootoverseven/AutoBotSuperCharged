import pandas as pd
import numpy as np
from fyers_apiv3 import fyersModel
import time
from datetime import datetime, timedelta
import openpyxl
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration variables
PRIMARY_TIMEFRAME = "5"  # 5-minute candles
SECONDARY_TIMEFRAME = "15"  # 15-minute candles for confirmation
CANDLES_TO_ANALYZE = 10  # Number of candles to analyze for patterns
RISK_REWARD_RATIO = 2  # Fixed 1:2 risk-reward ratio
PAPER_TRADING = False  # Set to False for live trading
PAPER_TRADING_BALANCE = 100000  # Set your desired paper trading balance

# Load API credentials
client_id = open("client_id.txt", 'r').read().strip()
access_token = open("access_token.txt", 'r').read().strip()
# Initialize Fyers API
fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token)

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

def round_to_tick_size(price, tick_size=0.05):
    return round(price / tick_size) * tick_size

def get_historical_data(symbol, interval, days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Adjust end_date to the start of the current candle
    minutes_to_subtract = end_date.minute % int(interval)
    seconds_to_subtract = end_date.second
    end_date = end_date - timedelta(minutes=minutes_to_subtract, seconds=seconds_to_subtract)
    
    data = {
        "symbol": symbol,
        "resolution": interval,
        "date_format": "1",
        "range_from": start_date.strftime('%Y-%m-%d'),
        "range_to": end_date.strftime('%Y-%m-%d'),
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

    # Get the last CANDLES_TO_ANALYZE completed candles
    recent_candles = data.iloc[-CANDLES_TO_ANALYZE:]
    price_score = 0
    candle_sizes = []

    for i in range(CANDLES_TO_ANALYZE - 1):
        current_candle = recent_candles.iloc[i]
        next_candle = recent_candles.iloc[i+1] if i+1 < CANDLES_TO_ANALYZE else None
        candle_size = abs(current_candle['close'] - current_candle['open'])
        candle_sizes.append(candle_size)

        # Bullish candle
        if current_candle['close'] > current_candle['open']:
            price_score += 1
        # Bearish candle
        elif current_candle['close'] < current_candle['open']:
            price_score -= 1

        # Long lower wick (potential reversal)
        if (min(current_candle['open'], current_candle['close']) - current_candle['low']) > (0.5 * abs(current_candle['close'] - current_candle['open'])):
            price_score += 1 if current_candle['close'] > current_candle['open'] else -1

        # Long upper wick (potential reversal)
        if (current_candle['high'] - max(current_candle['open'], current_candle['close'])) > (0.5 * abs(current_candle['close'] - current_candle['open'])):
            price_score -= 1 if current_candle['close'] > current_candle['open'] else 1

        # Engulfing patterns
        if next_candle is not None:
            # Bullish engulfing
            if current_candle['close'] < current_candle['open'] and next_candle['close'] > next_candle['open'] and \
               next_candle['close'] > current_candle['open'] and next_candle['open'] < current_candle['close']:
                price_score += 2
            # Bearish engulfing
            elif current_candle['close'] > current_candle['open'] and next_candle['close'] < next_candle['open'] and \
                 next_candle['close'] < current_candle['open'] and next_candle['open'] > current_candle['close']:
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

def analyze_timeframe(symbol, interval):
    # Get 5 days of data for better analysis
    data = get_historical_data(symbol, interval, 5)
    if data.empty:
        print(f"No data available for {symbol} on {interval} timeframe")
        return None
    
    # Ensure we have enough data for analysis
    if len(data) < CANDLES_TO_ANALYZE:
        print(f"Insufficient data for {symbol} on {interval} timeframe. Got {len(data)} candles, need {CANDLES_TO_ANALYZE}.")
        return None

    price_analysis = analyze_price_action(data)
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
        'timestamp': last_completed_candle.name  # This will give you the timestamp of the last completed candle
    }

def select_best_stock(nifty_trend):
    nifty50_symbols = get_nifty50_symbols()
    stock_scores = []

    for symbol in nifty50_symbols:
        analysis_primary = analyze_timeframe(symbol, PRIMARY_TIMEFRAME)
        analysis_secondary = analyze_timeframe(symbol, SECONDARY_TIMEFRAME)

        if analysis_primary is None or analysis_secondary is None:
            continue

        total_score = analysis_primary['score'] + analysis_secondary['score']

        print(f"Stock: {symbol}, Primary Score: {analysis_primary['score']}, Secondary Score: {analysis_secondary['score']}, Total Score: {total_score}")

        # Modified logic to select stocks in both uptrend and downtrend
        if nifty_trend == "downtrend":
            if total_score < 0:  # Select stocks with negative scores for short trades in downtrend
                stock_scores.append((symbol, abs(total_score), analysis_primary['trend'], analysis_primary['atr'], "short"))
        else:  # uptrend
            if total_score > 0:  # Select stocks with positive scores for long trades in uptrend
                stock_scores.append((symbol, total_score, analysis_primary['trend'], analysis_primary['atr'], "long"))

    stock_scores.sort(key=lambda x: x[1], reverse=True)

    return stock_scores[0] if stock_scores else None

def place_bracket_order(symbol, qty, side, entry_price, stop_loss, take_profit):
    order_params = {
        "symbol": symbol,
        "qty": qty,
        "type": 2,
        "side": side,
        "productType": "BO",
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
        "stopLoss": round_to_tick_size(abs(entry_price - stop_loss)),
        "takeProfit": round_to_tick_size(abs(take_profit - entry_price))
    }
    print(f"Attempting to place bracket order with parameters: {order_params}")
    try:
        response = fyers.place_order(data=order_params)
        if response.get('s') == 'ok' and 'id' in response:
            print(f"Bracket order placed successfully. Order ID: {response['id']}")
            return response
        else:
            print(f"Bracket order placement failed. Response: {response}")
    except Exception as e:
        print(f"Error placing bracket order: {str(e)}")
    return None

def get_latest_price(symbol):
    data = {"symbols": symbol}
    try:
        response = fyers.quotes(data=data)
        if response.get('code') == 200:
            quotes = response.get('d', [])
            for quote in quotes:
                if quote['n'] == symbol:
                    return quote['v']['lp']
    except Exception as e:
        print(f"Error fetching latest price for {symbol}: {str(e)}")
    return None

def get_available_balance():
    try:
        response = fyers.funds()
        if response['s'] == 'ok' and response['code'] == 200:
            for item in response['fund_limit']:
                if item['title'] == 'Total Balance':
                    return item['equityAmount']
        print("Failed to fetch available balance")
        return None
    except Exception as e:
        print(f"Error fetching available balance: {str(e)}")
        return None

def get_quantity_based_on_price(symbol, paper_balance=None):
    current_price = get_latest_price(symbol)

    if PAPER_TRADING and paper_balance is not None:
        available_balance = paper_balance
    else:
        available_balance = get_available_balance()

    if current_price is None or available_balance is None:
        print(f"Unable to fetch latest price for {symbol} or available balance. Using default quantity of 1.")
        return 1

    usable_balance = available_balance * 0.95
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

def check_order_status(main_order_id):
    try:
        def get_order_details(order_id):
            response = fyers.orderbook(data={"id": order_id})
            if response.get('s') == 'ok' and response.get('orderBook'):
                return response['orderBook'][0]
            return None

        main_order = get_order_details(main_order_id)
        if not main_order:
            print(f"Main order not found for ID: {main_order_id}")
            return 'UNKNOWN', None, None

        sl_order_id = str(int(main_order_id) + 1)
        tp_order_id = str(int(main_order_id) + 2)

        sl_order = get_order_details(sl_order_id)
        tp_order = get_order_details(tp_order_id)

        status_map = {
            1: 'CANCELED', 2: 'FILLED', 4: 'TRANSIT',
            5: 'REJECTED', 6: 'PENDING', 7: 'EXPIRED'
        }

        main_status = status_map.get(main_order['status'], 'UNKNOWN')

        print(f"Main order status: {main_status}")
        if sl_order:
            print(f"SL order status: {status_map.get(sl_order['status'], 'UNKNOWN')}")
        if tp_order:
            print(f"TP order status: {status_map.get(tp_order['status'], 'UNKNOWN')}")

        if main_status == 'FILLED':
            if sl_order and sl_order['status'] == 2:
                return 'SL_HIT', sl_order.get('tradedPrice', 0), main_order.get('tradedPrice', 0)
            elif tp_order and tp_order['status'] == 2:
                return 'TP_HIT', tp_order.get('tradedPrice', 0), main_order.get('tradedPrice', 0)
            else:
                return 'OPEN', None, main_order.get('tradedPrice', 0)
        elif main_status in ['CANCELED', 'REJECTED', 'EXPIRED']:
            return 'CLOSED', None, None
        elif main_status == 'PENDING':
            return 'PENDING', None, None
        else:
            return 'OPEN', None, None

    except Exception as e:
        print(f"Error checking order status for ID {main_order_id}: {str(e)}")
        return 'UNKNOWN', None, None

def is_new_candle(interval: str) -> bool:
    current_time = datetime.now()
    interval_minutes = int(interval)
    minutes_past = current_time.minute % interval_minutes
    seconds_past = current_time.second
    
    return minutes_past == 0 and seconds_past < 10  # Allow a 10-second window

def get_current_price(symbol):
    data = {"symbols": symbol}

    response = fyers.quotes(data=data)

    if response['s'] == 'ok' and response['code'] == 200:
        for quote in response['d']:
            if quote['n'] == symbol:
                ltp = quote['v']['lp']
                return float(ltp)

        print(f"Symbol {symbol} not found in the response")
        return None
    else:
        print(f"Error fetching price for {symbol}: {response.get('message', 'Unknown error')}")
        return None

def modify_order(order_id, new_sl, new_tp):
    try:
        response = fyers.modify_order(order_id, sl_price=new_sl, tp_price=new_tp)
        if response['s'] == 'ok':
            print(f"Order modified successfully. New SL: {new_sl}, New TP: {new_tp}")
            return True
        else:
            print(f"Failed to modify order. Response: {response}")
    except Exception as e:
        print(f"Error modifying order: {str(e)}")
    return False

def generate_excel_report(trades):
    df = pd.DataFrame(trades, columns=['Symbol', 'Entry Time', 'Exit Time', 'Position', 'Entry Price', 'Exit Price', 'Quantity', 'P/L', 'Take Profit'])
    df['P/L'] = df['P/L'].astype(float)
    total_pnl = df['P/L'].sum()

    current_date = datetime.now().strftime("%Y-%m-%d")
    filename = f'trading_report_{current_date}.xlsx'

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Trades', index=False)

        workbook = writer.book
        worksheet = writer.sheets['Trades']

        # Add summary
        worksheet['A{}'.format(len(df) + 3)] = 'Total P/L'
        worksheet['B{}'.format(len(df) + 3)] = total_pnl

        # Add some formatting
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

    print(f"Excel report generated: {filename}")

def update_live_chart(symbol, data, entry_price, stop_loss, take_profit):
    # Create subplot with 2 rows (price and volume)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(symbol, 'Volume'),
                        row_heights=[0.7, 0.3])

    # Add candlestick chart
    fig.add_trace(go.Candlestick(x=data.index,
                                 open=data['open'],
                                 high=data['high'],
                                 low=data['low'],
                                 close=data['close'],
                                 name='Price'))

    # Add volume bar chart
    fig.add_trace(go.Bar(x=data.index, y=data['volume'], name='Volume'), row=2, col=1)

    # Add entry, stop loss, and take profit lines
    fig.add_hline(y=entry_price, line_dash="dash", line_color="green", annotation_text="Entry")
    fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text="Stop Loss")
    fig.add_hline(y=take_profit, line_dash="dash", line_color="blue", annotation_text="Take Profit")

    # Update layout for better readability
    fig.update_layout(height=800, title_text=f"Live Chart for {symbol}")
    fig.update_xaxes(rangeslider_visible=False)

    # Show the plot
    fig.show()

def main():
    print("hello")
    position = 0
    order_id = None
    entry_price = stop_loss = take_profit = 0
    symbol = None
    qty = 0
    risk_reward_ratio = RISK_REWARD_RATIO
    unknown_status_count = 0
    last_traded_symbol = None
    consecutive_attempts = 0
    entry_time = None
    trades = []  # List to store completed trades

    while True:
        current_time = datetime.now().time()
        if current_time >= datetime.strptime("15:30", "%H:%M").time():
            print("Market closed. Ending script.")
            break

        if position != 0 or order_id is not None:
            print("Trade is ongoing. Checking status.")

            latest_data = get_historical_data(symbol, PRIMARY_TIMEFRAME, 1)  # Get 1 day of recent data
            
            # if not latest_data.empty:
                # Update the live chart
                # update_live_chart(symbol, latest_data, entry_price, stop_loss, take_profit)
            
            if PAPER_TRADING:
                current_price = get_current_price(symbol)
                if current_price:
                    if (position == 1 and current_price <= stop_loss) or (position == -1 and current_price >= stop_loss):
                        exit_price = stop_loss
                        exit_type = "SL_HIT"
                    elif (position == 1 and current_price >= take_profit) or (position == -1 and current_price <= take_profit):
                        exit_price = take_profit
                        exit_type = "TP_HIT"
                    else:
                        exit_price = None
                        exit_type = None
                    
                    if exit_price:
                        pnl = (exit_price - entry_price) * position * qty
                        print(f"Paper trade completed. Exit type: {exit_type}, Exit price: {exit_price}, P/L: {pnl:.2f}")
                        trades.append([symbol, entry_time, datetime.now(), "Long" if position == 1 else "Short", entry_price, exit_price, qty, pnl, take_profit])
                        generate_excel_report(trades)
                        position = 0
                        order_id = None
                        entry_price = stop_loss = take_profit = 0
                        symbol = None
                        qty = 0
                        last_traded_symbol = None
                        consecutive_attempts = 0
                        entry_time = None
                else:
                    print("Failed to get current price for paper trade. Skipping this cycle.")
            else:
                order_status, exit_price, filled_entry_price = check_order_status(order_id)
                print(f"Current order status: {order_status}")
                
                if order_status in ['SL_HIT', 'TP_HIT']:
                    print(f"Trade completed. Exit price: {exit_price}")
                    if filled_entry_price:
                        pnl = (exit_price - filled_entry_price) * position * qty
                        print(f"Trade completed. P/L: {pnl:.2f}")
                        trades.append([symbol, entry_time, datetime.now(), "Long" if position == 1 else "Short", filled_entry_price, exit_price, qty, pnl, take_profit])
                        generate_excel_report(trades)
                    position = 0
                    order_id = None
                    entry_price = stop_loss = take_profit = 0
                    symbol = None
                    qty = 0
                    last_traded_symbol = None
                    consecutive_attempts = 0
                elif order_status == 'CLOSED':
                    print("Order closed. Resetting position.")
                    position = 0
                    order_id = None
                    entry_price = stop_loss = take_profit = 0
                    symbol = None
                    qty = 0
                    last_traded_symbol = None
                    consecutive_attempts = 0
                elif order_status == 'PENDING':
                    print("Order is pending. Waiting for execution.")
                elif order_status == 'OPEN':
                    print(f"Order is open. Entry: {filled_entry_price}, Current SL: {stop_loss}, Current TP: {take_profit}")
                elif order_status == 'UNKNOWN':
                    print(f"Unable to determine order status. Will retry in next iteration.")
                    unknown_status_count += 1
                    if unknown_status_count >= 10:  # Reset after 10 consecutive unknown statuses
                        print("Resetting trade after multiple unknown statuses")
                        position = 0
                        order_id = None
                        entry_price = stop_loss = take_profit = 0
                        symbol = None
                        qty = 0
                        last_traded_symbol = None
                        consecutive_attempts = 0
                        unknown_status_count = 0
                else:
                    unknown_status_count = 0  # Reset counter if we get a known status
            
            time.sleep(15)
            continue
        
        # Check if a new candle has just started
        if not is_new_candle(PRIMARY_TIMEFRAME):
            print("Waiting for new candle to start...")
            time.sleep(10)  # Wait for 10 seconds before checking again
            continue
        
        print(f"New candle started. Beginning analysis at {datetime.now()}")

        print(f"No ongoing trade. Starting new trading cycle at {datetime.now()}")
        
        # Nifty trend analysis
        nifty_data = get_historical_data("NSE:NIFTY50-INDEX", PRIMARY_TIMEFRAME, 1)
        if nifty_data.empty:
            print("Failed to fetch Nifty 50 data. Retrying in 5 seconds.")
            time.sleep(5)
            continue

        nifty_trend = "uptrend" if nifty_data['close'].iloc[-1] > nifty_data['close'].iloc[-10] else "downtrend"
        print(f"Nifty 50 is currently in a {nifty_trend}.")

        # Stock selection and analysis
        best_stock = select_best_stock(nifty_trend)
        if not best_stock:
            print("No suitable stocks found for trading. Retrying in 30 seconds.")
            time.sleep(30)
            continue

        symbol, total_score, trend, atr, trade_type = best_stock
        print(f"Best stock for trading: {symbol} with Total Score: {total_score:.2f}, Trend: {trend}, ATR: {atr:.2f}, Trade Type: {trade_type}")

        # Check if we're repeatedly attempting to trade the same stock
        if symbol == last_traded_symbol:
            consecutive_attempts += 1
            if consecutive_attempts >= 3:
                print(f"Skipping {symbol} after {consecutive_attempts} consecutive attempts.")
                time.sleep(300)
                continue
        else:
            last_traded_symbol = symbol
            consecutive_attempts = 1

        current_price = get_current_price(symbol)
        print(f"Current price for {symbol}: {current_price}")
        if not current_price:
            print("Failed to get current price. Skipping this cycle.")
            time.sleep(15)
            continue

        if PAPER_TRADING:
            qty = get_quantity_based_on_price(symbol, PAPER_TRADING_BALANCE)
        else:
            qty = get_quantity_based_on_price(symbol)
        print(f"Quantity for {symbol} set to: {qty}")

        if trade_type == "long":
            entry_price = current_price
            initial_stop_loss = round_to_tick_size(entry_price - atr)
            take_profit = round_to_tick_size(entry_price + (atr * risk_reward_ratio))
            print(f"Attempting to place LONG order - LTP: {entry_price}, SL: {initial_stop_loss}, TP: {take_profit}")
            if PAPER_TRADING:
                position = 1
                stop_loss = initial_stop_loss
                entry_time = datetime.now()
                print(f"Entered paper long position. Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            else:
                order_response = place_bracket_order(symbol, qty, 1, entry_price, initial_stop_loss, take_profit)
                if order_response:
                    order_id = order_response['id']
                    position = 1
                    stop_loss = initial_stop_loss
                    entry_time = datetime.now()
                    print(f"Entered long position. Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, Order ID: {order_id}")

        elif trade_type == "short":
            entry_price = current_price
            initial_stop_loss = round_to_tick_size(entry_price + atr)
            take_profit = round_to_tick_size(entry_price - (atr * risk_reward_ratio))
            print(f"Attempting to place SHORT order - LTP: {entry_price}, SL: {initial_stop_loss}, TP: {take_profit}")
            if PAPER_TRADING:
                position = -1
                stop_loss = initial_stop_loss
                entry_time = datetime.now()
                print(f"Entered paper short position. Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            else:
                order_response = place_bracket_order(symbol, qty, -1, entry_price, initial_stop_loss, take_profit)
                if order_response:
                    order_id = order_response['id']
                    position = -1
                    stop_loss = initial_stop_loss
                    entry_time = datetime.now()
                    print(f"Entered short position. Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, Order ID: {order_id}")

        else:
            print(f"No suitable trade setup found for {symbol}")

        time.sleep(15)

if __name__ == "__main__":
    main()
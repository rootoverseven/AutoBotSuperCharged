import time
from datetime import datetime
from src.fyers_api.connection import FyersConnection
from src.utils.data_fetcher import get_historical_data
from src.utils.excel_report import generate_excel_report

class TradingBot:
    def __init__(self, strategy, config):
        self.strategy = strategy
        self.config = config
        self.fyers = FyersConnection(config['CLIENT_ID'], config['ACCESS_TOKEN'])
        self.paper_trades = []
        self.order_id = None
        self.position = 0
        self.entry_price = self.stop_loss = self.take_profit = 0
        print("Initializing TradingBot with config:", config)

    def round_to_tick_size(self, price, tick_size=0.05):
        return round(price / tick_size) * tick_size
    
    def get_current_price(self, symbol):
        data = {"symbols": symbol}

        response = self.fyers.get_quotes([symbol])

        symbol_data = response[symbol]
        if 'lp' not in symbol_data:
            raise KeyError(f"'lp' key not found in data for symbol {symbol}")
        current_price = symbol_data['lp']
        print(f"Current price: {current_price}")

        return current_price

        # if response['s'] == 'ok' and response['code'] == 200:
        #     for quote in response['d']:
        #         if quote['n'] == symbol:
        #             ltp = quote['v']['lp']
        #             return float(ltp)

        #     print(f"Symbol {symbol} not found in the response")
        #     return None
        # else:
        #     print(f"Error fetching price for {symbol}: {response.get('message', 'Unknown error')}")
        #     return None

    def run(self):
        last_traded_symbol = None
        print("Starting TradingBot run...")
        while True:
            current_time = datetime.now().time()
            print(f"Current time: {current_time}")
            # if current_time >= datetime.strptime("15:30", "%H:%M").time():
            #     print("Market closed. Generating report and ending script.")
            #     self.generate_report()
            #     break

            print("Fetching Nifty 50 data...")
            nifty_data = get_historical_data(self.fyers, "NSE:NIFTY50-INDEX", self.config['PRIMARY_TIMEFRAME'], 1)
            if nifty_data.empty:
                print("Failed to fetch Nifty 50 data. Retrying in 5 seconds.")
                time.sleep(5)
                continue

            nifty_trend = "uptrend" if nifty_data['close'].iloc[-1] > nifty_data['close'].iloc[-10] else "downtrend"
            print(f"Nifty 50 is currently in a {nifty_trend}.")

            tradable_symbols = self.get_tradable_symbols()
            print(f"Tradable symbols: {tradable_symbols}")

            best_stock = self.strategy.select_best_stock(self, tradable_symbols, nifty_trend)
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
            
            current_price = self.get_current_price(symbol)
            if not current_price:
                print("Failed to get current price. Skipping this cycle.")
                time.sleep(15)
                continue

            quantity = self.calculate_quantity(current_price)
            print(f"Calculated quantity: {quantity}")
            
            side = 1 if trade_type == "long" else -1
            print(f"Trade side: {'Buy' if side == 1 else 'Sell'}")

            self.place_trade(symbol, quantity, side, current_price, atr)
                        

            # for symbol in tradable_symbols:
            #     print(f"\nProcessing symbol: {symbol}")
            #     print("Fetching primary timeframe data...")
            #     primary_data = get_historical_data(self.fyers, symbol, self.config['PRIMARY_TIMEFRAME'], 5)
            #     print("Fetching secondary timeframe data...")
            #     secondary_data = get_historical_data(self.fyers, symbol, self.config['SECONDARY_TIMEFRAME'], 5)

            #     if primary_data.empty or secondary_data.empty:
            #         print(f"Failed to fetch data for {symbol}. Skipping.")
            #         continue

            #     print("Analyzing data...")
            #     analysis_result = self.strategy.analyze(symbol, primary_data, secondary_data)
            #     print(f"Analysis result: {analysis_result}")

            #     should_trade = self.strategy.appendStockScore(analysis_result, nifty_trend)
            #     print(f"Should enter trade: {should_trade}")

            #     if should_trade:
            #         print("Preparing to place trade...")
            #         try:
            #             quotes = self.fyers.get_quotes([symbol])
            #             print(f"API response for quotes: {quotes}")  # Log the full response

            #             if symbol not in quotes:
            #                 raise KeyError(f"Symbol {symbol} not found in the API response")

            #             symbol_data = quotes[symbol]
            #             if 'lp' not in symbol_data:
            #                 raise KeyError(f"'lp' key not found in data for symbol {symbol}")

            #             current_price = symbol_data['lp']
            #             print(f"Current price: {current_price}")

            #             quantity = self.calculate_quantity(current_price)
            #             print(f"Calculated quantity: {quantity}")

            #             side = 1 if analysis_result['total_score'] > 0 else -1
            #             print(f"Trade side: {'Buy' if side == 1 else 'Sell'}")

            #             self.place_trade(symbol, quantity, side, current_price, analysis_result['atr'])
            #             break
            #         except KeyError as e:
            #             print(f"KeyError occurred: {str(e)}")
            #         # Handle the error (e.g., skip this trade, use alternative data source, etc.)
            #         except Exception as e:
            #             print(f"An unexpected error occurred: {str(e)}")
            #             # Handle any other unexpected errors
            print("Waiting for 60 seconds before next iteration...")
            time.sleep(60)

    def place_trade(self, symbol, quantity, side, current_price, atr):
        stop_loss = current_price - (side * atr)
        take_profit = current_price + (side * atr * self.config['RISK_REWARD_RATIO'])
        print(f"Placing trade for {symbol}:")
        print(f"  Quantity: {quantity}")
        print(f"  Side: {'Buy' if side == 1 else 'Sell'}")
        print(f"  Entry Price: {current_price}")
        print(f"  Stop Loss: {stop_loss}")
        print(f"  Take Profit: {take_profit}")

        if self.config['PAPER_TRADING']:
            print("Paper trading mode:")
            print(f"Paper trade placed: {symbol}, Qty: {quantity}, Side: {'Buy' if side == 1 else 'Sell'}, Entry: {current_price}, SL: {stop_loss}, TP: {take_profit}")
            self.paper_trades.append({
                'symbol': symbol,
                'entry_time': datetime.now(),
                'side': 'Long' if side == 1 else 'Short',
                'entry_price': current_price,
                'quantity': quantity,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            })
        else:
            print("Live trading mode:")
            order_params = {
                "symbol": symbol,
                "qty": quantity,
                "type": 2,  # Market order
                "side": side,
                "productType": "BO",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False,
                "stopLoss": self.round_to_tick_size(abs(current_price - stop_loss)),
                "takeProfit": self.round_to_tick_size(abs(take_profit - current_price))
            }
            print("Order parameters:", order_params)
            self.position = side
            self.stop_loss = stop_loss
            self.take_profit = take_profit
            response = self.fyers.place_order(order_params)
            print(f"Order placed response: {response}")

    def calculate_quantity(self, current_price):
        if self.config['PAPER_TRADING']:
            capital = self.config['PAPER_TRADING_BALANCE']
        else:
            capital = self.fyers.get_funds()['equityAmount']
        
        risk_per_trade = capital * 0.01  # Risk 1% per trade
        quantity = int(risk_per_trade / (current_price * 0.01))  # Assume 1% stop loss
        print(f"Quantity calculation:")
        print(f"  Capital: {capital}")
        print(f"  Risk per trade: {risk_per_trade}")
        print(f"  Calculated quantity: {quantity}")
        return max(1, quantity)  # Ensure at least 1 quantity

    def get_tradable_symbols(self):
        # Implement logic to get a list of tradable symbols
        # This could be a predefined list or fetched from an external source
        symbols = ["NSE:ADANIENT-EQ", "NSE:ADANIPORTS-EQ", "NSE:APOLLOHOSP-EQ", "NSE:ASIANPAINT-EQ", "NSE:AXISBANK-EQ",
        "NSE:BAJAJ-AUTO-EQ", "NSE:BAJFINANCE-EQ", "NSE:BAJAJFINSV-EQ", "NSE:BPCL-EQ", "NSE:BHARTIARTL-EQ",
        "NSE:BRITANNIA-EQ", "NSE:CIPLA-EQ", "NSE:COALINDIA-EQ", "NSE:DIVISLAB-EQ", "NSE:DRREDDY-EQ",
        "NSE:EICHERMOT-EQ", "NSE:GRASIM-EQ", "NSE:HCLTECH-EQ", "NSE:HDFCBANK-EQ", "NSE:HDFCLIFE-EQ",
        "NSE:HEROMOTOCO-EQ", "NSE:HINDALCO-EQ", "NSE:HINDUNILVR-EQ", "NSE:ICICIBANK-EQ", "NSE:INDUSINDBK-EQ",
        "NSE:INFY-EQ", "NSE:ITC-EQ", "NSE:JSWSTEEL-EQ", "NSE:KOTAKBANK-EQ", "NSE:LT-EQ",
        "NSE:M&M-EQ", "NSE:MARUTI-EQ", "NSE:NESTLEIND-EQ", "NSE:NTPC-EQ", "NSE:ONGC-EQ",
        "NSE:POWERGRID-EQ", "NSE:RELIANCE-EQ", "NSE:SBILIFE-EQ", "NSE:SBIN-EQ", "NSE:SUNPHARMA-EQ",
        "NSE:TCS-EQ", "NSE:TATACONSUM-EQ", "NSE:TATAMOTORS-EQ", "NSE:TATASTEEL-EQ", "NSE:TECHM-EQ",
        "NSE:TITAN-EQ", "NSE:ULTRACEMCO-EQ", 
        "NSE:UPL-EQ", "NSE:WIPRO-EQ"]  # Example symbols
        print(f"Fetched tradable symbols: {symbols}")
        return symbols

    def generate_report(self):
        print("Generating Excel report...")
        generate_excel_report(self.paper_trades)
        print("Report generation complete.")
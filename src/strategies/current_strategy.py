from src.strategies.base_strategy import TradingStrategy
from src.analysis.price_action import analyze_price_action
from src.analysis.price_action import analyze_volume
from src.analysis.indicators import calculate_atr
from src.utils.data_fetcher import get_historical_data

# Rest of the code remains the same

class CurrentStrategy(TradingStrategy):
    def analyze(self, symbol, primary_data, secondary_data):
        primary_analysis = analyze_price_action(primary_data)
        primary_volume_score = analyze_volume(primary_data)
        secondary_analysis = analyze_price_action(secondary_data)
        secondary_volume_score = analyze_volume(secondary_data)
        atr = calculate_atr(primary_data)
        return {
            'symbol': symbol,
            'primary': primary_analysis,
            'secondary': secondary_analysis,
            'atr': atr,
            'total_score': primary_analysis['price_score'] + secondary_analysis['price_score'] + primary_volume_score + secondary_volume_score
        }

    def appendStockScore(self, analysis_result, nifty_trend, stock_scores, symbol):
        total_score = analysis_result['total_score']
        primary_trend = analysis_result['primary']['trend']
        secondary_trend = analysis_result['secondary']['trend']
        print(f"Score is {total_score}")
        if nifty_trend == "downtrend":
            if total_score < 0:  # Select stocks with negative scores for short trades in downtrend
                stock_scores.append((symbol, abs(total_score), primary_trend, analysis_result['atr'], "short"))
        else:  # uptrend
            if total_score > 0:  # Select stocks with positive scores for long trades in uptrend
                stock_scores.append((symbol, total_score, primary_trend, analysis_result['atr'], "long"))


    
    def select_best_stock(self, tBot, tradable_symbols, nifty_trend):
        stock_scores = []
        for symbol in tradable_symbols:
            print(f"\nProcessing symbol: {symbol}")
            print("Fetching primary timeframe data...")
            primary_data = get_historical_data(tBot.fyers, symbol, tBot.config['PRIMARY_TIMEFRAME'], 5)
            print("Fetching secondary timeframe data...")
            secondary_data = get_historical_data(tBot.fyers, symbol, tBot.config['SECONDARY_TIMEFRAME'], 5)

            if primary_data.empty or secondary_data.empty:
                print(f"Failed to fetch data for {symbol}. Skipping.")
                continue

            # print("Analyzing data...")
            analysis_result = self.analyze(symbol, primary_data, secondary_data)
            # print(f"Analysis result: {analysis_result}")

            self.appendStockScore(analysis_result, nifty_trend, stock_scores, symbol)
            # print(f"Should enter trade: {should_trade}")
            print(f"Stock: {symbol}, Total Score: {analysis_result['total_score']}")

        stock_scores.sort(key=lambda x: x[1], reverse=True)
        return stock_scores[0] if stock_scores else None
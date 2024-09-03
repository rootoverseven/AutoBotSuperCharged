from src.trading_bot import TradingBot
from src.strategies.current_strategy import CurrentStrategy
from src.config import load_config

def main():
    config = load_config()
    strategy = CurrentStrategy()
    bot = TradingBot(strategy, config)
    bot.run()

if __name__ == "__main__":
    main()
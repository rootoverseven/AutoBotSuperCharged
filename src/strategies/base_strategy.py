from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    @abstractmethod
    def analyze(self, symbol, primary_data, secondary_data):
        pass

    @abstractmethod
    def appendStockScore(self, analysis_result, nifty_trend):
        pass

    @abstractmethod
    def select_best_stock(self, tradable_symbols, nifty_trend):
        pass
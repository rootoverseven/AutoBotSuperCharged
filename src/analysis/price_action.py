import numpy as np
from src.config import load_config

def analyze_price_action(data):
    config = load_config()
    CANDLES_TO_ANALYZE = config['CANDLES_TO_ANALYZE']

    if len(data) < CANDLES_TO_ANALYZE: #use varriable
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

    return {
        "price_score": price_score,
        "trend": trend,
        "volatility": volatility
    }

def analyze_volume(data):
    config = load_config()
    CANDLES_TO_ANALYZE = config['CANDLES_TO_ANALYZE']
    
    if len(data) < CANDLES_TO_ANALYZE: #use variable
        return 0

    avg_volume = data['volume'].rolling(window=CANDLES_TO_ANALYZE).mean() #use variable
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
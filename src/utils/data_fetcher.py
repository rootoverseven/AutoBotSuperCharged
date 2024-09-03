import pandas as pd
from datetime import datetime, timedelta

def get_historical_data(fyers, symbol, interval, days):
    end_date = datetime.now().strftime('%Y-%m-%d')
    # end_date = '2024-08-09'
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    # start_date = '2024-08-08'
    print(start_date)
    print(end_date)
    data = {
        "symbol": symbol,
        "resolution": interval,
        "date_format": "1",
        "range_from": start_date,
        "range_to": end_date,
        "cont_flag": "1"
    }
    
    try:
        response = fyers.fyers.history(data=data)
        # print(f"API Response: {response}")  # Add this line to print the full response
        if 'candles' in response:
            df = pd.DataFrame(response['candles'], columns=["timestamp", "open", "high", "low", "close", "volume"])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            return df
        else:
            print(f"Error in response: {response}")  # Add this line to print error details
    except Exception as e:
        print(f"Exception while fetching historical data for {symbol}: {str(e)}")
    
    return pd.DataFrame()
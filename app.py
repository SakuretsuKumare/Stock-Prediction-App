from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

def analyze_market(ticker, interval):
    try:
        # 1. SMART FETCHING LOGIC
        # We must adjust the 'period' so we always have enough candles for the 50-EMA math.
        # We also map intervals yfinance doesn't support to ones it does (to be resampled later).
        if interval == "1m":
            yf_interval, period = "1m", "5d"
        elif interval == "3m":
            yf_interval, period = "1m", "5d"   # Resampled later
        elif interval == "5m":
            yf_interval, period = "5m", "1mo"
        elif interval == "10m":
            yf_interval, period = "5m", "1mo"  # Resampled later
        elif interval == "15m":
            yf_interval, period = "15m", "1mo"
        elif interval == "30m":
            yf_interval, period = "30m", "1mo"
        elif interval == "45m":
            yf_interval, period = "15m", "1mo" # Resampled later
        elif interval == "1h":
            yf_interval, period = "1h", "3mo"  # Need 3 months to get enough 1h candles
        else:
            yf_interval, period = "1m", "5d"

        # Download the data
        df = yf.download(ticker, period=period, interval=yf_interval, progress=False)
        
        if df.empty:
            return None

        # Clean up multi-index columns (common in new versions of yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. CUSTOM RESAMPLING
        # Compress the data into perfect 3, 10, or 45-minute candles
        if interval in ["3m", "10m", "45m"]:
            # Match the exact string format Pandas needs (e.g., '3min')
            pandas_interval = interval.replace('m', 'min') 
            
            df = df.resample(pandas_interval).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        # --- MANUAL MATH ---
        
        # Calculate RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Calculate EMA (50)
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

        # Get the very last row (current moment)
        current = df.iloc[-1]
        
        # --- PREDICTION LOGIC ---
        up_score = 50.0 
        
        rsi_val = float(current['RSI'])
        close_val = float(current['Close'])
        ema_val = float(current['EMA_50'])
        
        if pd.isna(rsi_val) or pd.isna(ema_val):
            return None 
        
        # 1. Dynamic RSI Logic
        rsi_impact = (50 - rsi_val) * 0.75 
        up_score += rsi_impact
            
        # 2. Dynamic Trend Logic (EMA)
        diff_pct = ((close_val - ema_val) / ema_val) * 100
        
        ema_impact = diff_pct * 150  
        ema_impact = max(-25, min(25, ema_impact)) 
        
        up_score += ema_impact

        # Keep score safely between 5.0% and 95.0%
        up_score = max(5.0, min(95.0, up_score))
        down_score = 100.0 - up_score

        # Determine Signal based on exact decimal
        prediction = "BUY" if up_score > 50 else "SELL"

        return {
            "symbol": ticker,
            "interval": interval,
            "current_price": round(close_val, 5),
            "prediction": prediction,
            "up_probability": f"{up_score:.1f}%",
            "down_probability": f"{down_score:.1f}%"
        }

    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/predict', methods=['GET'])
def predict():
    symbol = request.args.get('symbol', 'EURUSD=X')
    interval = request.args.get('interval', '1m')
    
    result = analyze_market(symbol, interval)
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": "Data unavailable or insufficient"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
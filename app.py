from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

def analyze_market(ticker, interval):
    try:
        yf_interval = interval
        period = "5d"

        # Handle YFinance limitations: it doesn't support 3m natively.
        if interval == "3m":
            yf_interval = "1m"

        df = yf.download(ticker, period=period, interval=yf_interval, progress=False)
        
        if df.empty:
            return None

        # Clean up multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Custom Resampling for 3-minute data
        if interval == "3m":
            df = df.resample('3min').agg({
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

        # Determine Signal based on exact decimal (UPDATED TO BUY/SELL)
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
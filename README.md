# Stock-Market-Analyzer



Predicts whether the particular stocks you want will go up or down within the next 1, 3, or 5 minutes. It will give you the percentage of likelihood of the chances of it becoming true based on past trends and Yahoo Finance data.
What my code does is it sends a message to Python to analyze the minute charts, then Python downloads the last 5 days of candle data and calculates the RSI and EMA on all the candles. Then based off of the calculations and probability, it will give a prediction on the specific time frame trend (based on the 1 minute trend for example)


To run this app, you need to run this command.
If you are on Windows = `pip install flask flask-cors yfinance pandas`
If you are on Mac = `pip3 install flask flask-cors yfinance pandas`


Then you just need to run `python .\app.py` and drag and drop the index.html into your browser. Have fun!


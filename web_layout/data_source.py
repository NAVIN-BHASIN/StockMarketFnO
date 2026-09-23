import yfinance as yf
import pandas as pd

class DataSource:
    """
    Pluggable data source for historical market data.
    """
    def __init__(self):
        pass

    def fetch_historical_yfinance(self, symbol, timeframe):
        """
        Fetch historical data from Yahoo Finance.
        yfinance valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
        """
        # Map frontend timeframe to yfinance interval
        tf_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "4h": "1h", # yf doesn't have 4h, using 1h as closest or fallback
            "1d": "1d",
            "1w": "1wk"
        }
        interval = tf_map.get(timeframe, "1d")
        
        # Period based on interval
        period = "1y"
        if interval in ["1m", "2m", "5m"]:
            period = "5d"
        elif interval in ["15m", "30m", "60m", "1h"]:
            period = "1mo"
            
        try:
            target_sym = symbol
            # Append .NS for Indian stocks if not an index and doesn't already have it
            if not target_sym.endswith(".NS") and not target_sym.startswith("^") and "-" not in target_sym:
                target_sym = f"{symbol}.NS"
                
            ticker = yf.Ticker(target_sym)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                return []
                
            # Convert to lightweight-charts format
            data = []
            for index, row in df.iterrows():
                # Lightweight charts expects time as unix timestamp (in seconds) or string 'yyyy-mm-dd'
                # Convert tz-aware to UTC timestamp
                timestamp = int(index.timestamp())
                data.append({
                    "time": timestamp,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "value": float(row['Volume'])
                })
            return data
        except Exception as e:
            print(f"Error fetching yfinance data for {symbol}: {e}")
            return []

    def fetch_historical_hyperliquid(self, symbol, timeframe):
        import requests
        import time
        
        # Hyperliquid valid intervals: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"
        tf_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w" 
        }
        interval = tf_map.get(timeframe, "1d")
        
        now_ms = int(time.time() * 1000)
        
        if interval in ["1m", "5m"]:
            start_ms = now_ms - (5 * 24 * 60 * 60 * 1000) # 5 days
        elif interval in ["15m", "30m", "1h", "4h"]:
            start_ms = now_ms - (30 * 24 * 60 * 60 * 1000) # 30 days
        else:
            start_ms = now_ms - (365 * 24 * 60 * 60 * 1000) # 1 year
            
        url = "https://api.hyperliquid.xyz/info"
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": now_ms
            }
        }
        try:
            res = requests.post(url, json=payload)
            res.raise_for_status()
            candles = res.json()
            
            data = []
            for c in candles:
                timestamp = int(c["t"] / 1000)
                data.append({
                    "time": timestamp,
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "value": float(c["v"])
                })
            return data
        except Exception as e:
            print(f"Error fetching hyperliquid data for {symbol}: {e}")
            return []

    # Skeleton for other brokers
    def fetch_historical_alpaca(self, symbol, timeframe):
        raise NotImplementedError("Alpaca data source not implemented yet.")
        
    def fetch_historical_binance(self, symbol, timeframe):
        raise NotImplementedError("Binance data source not implemented yet.")

    def get_data(self, broker, symbol, timeframe):
        if broker == "yfinance":
            return self.fetch_historical_yfinance(symbol, timeframe)
        elif broker == "hyperliquid":
            return self.fetch_historical_hyperliquid(symbol, timeframe)
        elif broker == "alpaca":
            return self.fetch_historical_alpaca(symbol, timeframe)
        elif broker == "binance":
            return self.fetch_historical_binance(symbol, timeframe)
        else:
            return []

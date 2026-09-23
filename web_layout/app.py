from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
from data_source import DataSource
import threading
import yfinance as yf

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests
ds = DataSource()

@app.route('/')
def index():
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/api/historical')
def historical():
    broker = request.args.get('broker', 'yfinance')
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1d')
    
    data = ds.get_data(broker, symbol, timeframe)
    return jsonify(data)

@app.route('/api/quote')
def quote():
    """Fetch a single live quote for a symbol using yfinance (used for polling)."""
    symbol = request.args.get('symbol', 'RELIANCE')
    target_sym = symbol
    if not target_sym.endswith(".NS") and not target_sym.startswith("^") and "-" not in target_sym:
        target_sym = f"{symbol}.NS"
        
    try:
        ticker = yf.Ticker(target_sym)
        # Fast live price fetch
        data = ticker.fast_info
        last_price = data.last_price
        
        return jsonify({
            "symbol": symbol,
            "price": float(last_price)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/compare')
def compare():
    symbols_param = request.args.get('symbols', '')
    benchmark = request.args.get('benchmark', '^NSEI')
    timeframe = request.args.get('timeframe', '1mo') 
    
    symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
        
    all_syms = symbols + [benchmark]
    
    period = timeframe
    if period not in ['1wk', '1mo', '3mo', '6mo', '1y', 'ytd', 'max']:
        period = '1mo'
        
    results = {}
    chart_data = {}
    
    try:
        valid_tickers = []
        for s in all_syms:
            t = s
            if not t.endswith(".NS") and not t.startswith("^") and "-" not in t:
                t = f"{s}.NS"
            valid_tickers.append(t)
            
        df = yf.download(valid_tickers, period=period, interval="1d", group_by='ticker', threads=True, progress=False)
        
        for i, sym in enumerate(all_syms):
            t = valid_tickers[i]
            
            if len(valid_tickers) == 1:
                stock_df = df
            else:
                if t in df.columns.levels[0] if isinstance(df.columns, pd.MultiIndex) else [t]:
                    stock_df = df[t] if isinstance(df.columns, pd.MultiIndex) else df
                else:
                    stock_df = pd.DataFrame()
            
            if stock_df.empty or stock_df['Close'].dropna().empty:
                results[sym] = {"error": "No data"}
                continue
                
            close_prices = stock_df['Close'].dropna()
            volume_data = stock_df['Volume'].dropna() if 'Volume' in stock_df else pd.Series(dtype=float)
            
            start_price = float(close_prices.iloc[0])
            end_price = float(close_prices.iloc[-1])
            profit_pct = ((end_price - start_price) / start_price) * 100
            
            total_vol = float(volume_data.sum()) if not volume_data.empty else 0
            
            series = []
            for date, price in close_prices.items():
                norm_price = (float(price) / start_price) * 100
                
                # Fix timestamp - yfinance returns timestamps at 00:00:00 but Lightweight Charts wants it as string 'YYYY-MM-DD' for daily
                series.append({"time": date.strftime('%Y-%m-%d'), "value": norm_price})
                
            chart_data[sym] = series
            
            results[sym] = {
                "start_price": start_price,
                "end_price": end_price,
                "profit_pct": profit_pct,
                "volume": total_vol
            }
            
        return jsonify({
            "metrics": results,
            "chart": chart_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_server():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()

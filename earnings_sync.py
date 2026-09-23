import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from db_utils import DatabaseHelper

def process_symbol(symbol):
    try:
        import warnings
        warnings.filterwarnings("ignore")
        target = f"{symbol}.NS" if not symbol.startswith('^') else symbol
        
        # Suppress yfinance stdout/stderr for cleaner console
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            tk = yf.Ticker(target)
            
            # 1. Get Earnings Calendar
        cal_data = []
        try:
            cal = tk.calendar
            if cal is not None:
                if isinstance(cal, pd.DataFrame) and not cal.empty:
                    if 'Earnings Date' in cal.index:
                        dates = cal.loc['Earnings Date']
                        for d in dates:
                            if pd.notna(d):
                                cal_data.append({'Symbol': symbol, 'Earnings_Date': pd.to_datetime(d).date()})
                elif isinstance(cal, dict) and 'Earnings Date' in cal:
                    for d in cal['Earnings Date']:
                        if pd.notna(d):
                            cal_data.append({'Symbol': symbol, 'Earnings_Date': pd.to_datetime(d).date()})
        except Exception:
            pass
            
        # 2. Get Quarterly Financials
        res_data = []
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                fin = tk.quarterly_income_stmt
            if fin is not None and not fin.empty and len(fin.columns) > 0:
                dates = sorted(list(fin.columns), reverse=True) # newest first
                
                for i, dt in enumerate(dates):
                    col = fin[dt]
                    rev = col.get('Total Revenue', 0)
                    gp = col.get('Gross Profit', 0)
                    np_val = col.get('Net Income', 0)
                    
                    if pd.isna(rev): rev = 0
                    if pd.isna(gp): gp = 0
                    if pd.isna(np_val): np_val = 0
                    
                    # Calculate QoQ
                    rev_qoq = gp_qoq = np_qoq = None
                    if i + 1 < len(dates):
                        prev_q = fin[dates[i+1]]
                        p_rev = prev_q.get('Total Revenue', 0)
                        p_gp = prev_q.get('Gross Profit', 0)
                        p_np = prev_q.get('Net Income', 0)
                        if p_rev and p_rev > 0: rev_qoq = (rev - p_rev) / p_rev * 100
                        if p_gp and p_gp > 0: gp_qoq = (gp - p_gp) / p_gp * 100
                        if p_np and p_np > 0: np_qoq = (np_val - p_np) / p_np * 100
                        
                    # Calculate YoY (approx 4 quarters back)
                    rev_yoy = gp_yoy = np_yoy = None
                    if i + 4 < len(dates):
                        prev_y = fin[dates[i+4]]
                        py_rev = prev_y.get('Total Revenue', 0)
                        py_gp = prev_y.get('Gross Profit', 0)
                        py_np = prev_y.get('Net Income', 0)
                        if py_rev and py_rev > 0: rev_yoy = (rev - py_rev) / py_rev * 100
                        if py_gp and py_gp > 0: gp_yoy = (gp - py_gp) / py_gp * 100
                        if py_np and py_np > 0: np_yoy = (np_val - py_np) / py_np * 100
                        
                    res_data.append({
                        'Symbol': symbol,
                        'Quarter_End': pd.to_datetime(dt).date(),
                        'Revenue': rev,
                        'Gross_Profit': gp,
                        'Net_Profit': np_val,
                        'Revenue_Growth_YoY': rev_yoy,
                        'Gross_Profit_Growth_YoY': gp_yoy,
                        'Net_Profit_Growth_YoY': np_yoy,
                        'Revenue_Growth_QoQ': rev_qoq,
                        'Gross_Profit_Growth_QoQ': gp_qoq,
                        'Net_Profit_Growth_QoQ': np_qoq
                    })
        except Exception:
            pass
            
        return cal_data, res_data
    except Exception as e:
        print(f"[{symbol}] Failed: {e}")
        return [], []

def run_sync():
    print("Starting Corporate Earnings Sync...")
    db = DatabaseHelper()
    
    print("Fetching All NSE cash stocks list...")
    df_fno = db.get_cash_stocks(index_filter="All")
    fno_symbols = df_fno['Symbol'].tolist() if not df_fno.empty else []
    
    if not fno_symbols:
        fno_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
        
    symbols_to_sync = fno_symbols
    print(f"Syncing {len(symbols_to_sync)} symbols using 10 threads...")
    
    all_cal = []
    all_res = []
    
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, sym): sym for sym in symbols_to_sync}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                cal, res = future.result()
                all_cal.extend(cal)
                all_res.extend(res)
                completed += 1
                if completed % 10 == 0:
                    print(f"Processed {completed}/{len(symbols_to_sync)} symbols...")
            except Exception as e:
                print(f"Error getting result for {sym}: {e}")
                
    print(f"Sync completed. Found {len(all_cal)} calendar dates and {len(all_res)} quarterly results.")
    
    if all_cal:
        print("Upserting calendar data...")
        cal_df = pd.DataFrame(all_cal)
        cal_df = cal_df.drop_duplicates(subset=['Symbol', 'Earnings_Date'])
        db.upsert_earnings_calendar(cal_df)
        
    if all_res:
        print("Upserting results data...")
        res_df = pd.DataFrame(all_res)
        import numpy as np
        res_df = res_df.replace({np.nan: None, float('inf'): None, float('-inf'): None})
        res_df = res_df.drop_duplicates(subset=['Symbol', 'Quarter_End'])
        db.upsert_earnings_results(res_df)
        
    print("Corporate Earnings Sync Finished successfully.")

if __name__ == "__main__":
    run_sync()

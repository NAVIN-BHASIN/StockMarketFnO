import pandas as pd
import pyodbc
from datetime import datetime
import numpy as np

server = r'.\SQLEXPRESS'
database = 'Navin_Personal'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

create_tbl = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TradingJournal_V2' and xtype='U')
CREATE TABLE TradingJournal_V2 (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Broker VARCHAR(50),
    Symbol VARCHAR(255),
    AssetClass VARCHAR(50),
    TradeType VARCHAR(50),
    EntryDate DATE,
    ExitDate DATE,
    Quantity INT,
    BuyValue FLOAT,
    SellValue FLOAT,
    GrossPnL FLOAT,
    TotalCharges FLOAT,
    NetPnL FLOAT,
    ROI_Pct FLOAT,
    HoldingDays INT
)
"""

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(create_tbl)
        cursor.execute("TRUNCATE TABLE TradingJournal_V2")
        conn.commit()
        
        file_path = r'C:\Users\navin\StockMarketFnO\data\journal\FY_2025_Journal.xlsx'
        xl = pd.ExcelFile(file_path)
        
        insert_query = """INSERT INTO TradingJournal_V2 
            (Broker, Symbol, AssetClass, TradeType, EntryDate, ExitDate, Quantity, BuyValue, SellValue, GrossPnL, TotalCharges, NetPnL, ROI_Pct, HoldingDays) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            
        total_rows = 0
        
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            
            for _, row in df.iterrows():
                try:
                    broker = sheet
                    symbol = "UNKNOWN"
                    asset_class = "Equity"
                    trade_type = "Long"
                    entry_date = None
                    exit_date = None
                    qty = 0
                    buy_val = 0.0
                    sell_val = 0.0
                    gross_pnl = 0.0
                    charges = 0.0
                    net_pnl = 0.0
                    roi_pct = 0.0
                    holding_days = 0
                    
                    if 'HDFC' in sheet:
                        symbol = str(row.get('Name', 'UNKNOWN'))
                        asset_class = str(row.get('Sub Asset', 'Equity'))
                        trade_type = str(row.get('Transaction Type', 'Long'))
                        
                        b_dt = row.get('Buy Transaction Date', row.get('Buy_Date', None))
                        s_dt = row.get('Sell Transaction Date', row.get('Sell_Date', None))
                        entry_date = pd.to_datetime(b_dt).date() if pd.notna(b_dt) else None
                        exit_date = pd.to_datetime(s_dt).date() if pd.notna(s_dt) else None
                        
                        qty = int(row.get('Buy Transaction Qty', row.get('Sell Transaction Qty', 0))) if pd.notna(row.get('Buy Transaction Qty', 0)) else 0
                        buy_val = float(row.get('Buy Transaction Value', 0.0)) if pd.notna(row.get('Buy Transaction Value', 0)) else 0.0
                        sell_val = float(row.get('Sell Transaction Value', 0.0)) if pd.notna(row.get('Sell Transaction Value', 0)) else 0.0
                        
                        gross_pnl = float(row.get('Gross P&L', 0.0)) if pd.notna(row.get('Gross P&L', 0)) else 0.0
                        net_pnl = float(row.get('Net Realized P&L', gross_pnl)) if pd.notna(row.get('Net Realized P&L', 0)) else gross_pnl
                        charges = float(row.get('Brokerage', 0)) + float(row.get('STT', 0)) + float(row.get('Transaction Charges', 0)) + float(row.get('Other Charges', 0))
                        
                        if pd.notna(row.get('Profit %')):
                            roi_pct = float(row['Profit %']) * 100 if float(row['Profit %']) < 10 else float(row['Profit %'])
                        else:
                            roi_pct = (net_pnl / buy_val * 100) if buy_val > 0 else 0.0
                            
                        if entry_date and exit_date:
                            holding_days = (exit_date - entry_date).days
                            
                    else:
                        # Best effort for Zerodha/BlinkX
                        cols = [str(c).lower() for c in df.columns]
                        
                        sym_col = next((c for c in df.columns if 'symbol' in str(c).lower() or 'instrument' in str(c).lower() or 'name' in str(c).lower()), None)
                        if sym_col: symbol = str(row[sym_col])
                        
                        dt_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
                        if dt_col: 
                            exit_date = pd.to_datetime(row[dt_col]).date() if pd.notna(row[dt_col]) else None
                            entry_date = exit_date
                            
                        qty_col = next((c for c in df.columns if 'qty' in str(c).lower() or 'quantity' in str(c).lower()), None)
                        if qty_col: qty = int(row[qty_col]) if pd.notna(row[qty_col]) else 0
                        
                        pnl_col = next((c for c in df.columns if 'p&l' in str(c).lower() or 'realized' in str(c).lower() or 'profit' in str(c).lower()), None)
                        if pnl_col: net_pnl = float(row[pnl_col]) if pd.notna(row[pnl_col]) else 0.0
                        
                        gross_pnl = net_pnl
                        
                    if not exit_date: exit_date = datetime.now().date()
                    if not entry_date: entry_date = exit_date
                    
                    cursor.execute(insert_query, (broker, symbol, asset_class, trade_type, entry_date, exit_date, qty, buy_val, sell_val, gross_pnl, charges, net_pnl, roi_pct, holding_days))
                    total_rows += 1
                except Exception as e:
                    pass
                    
        conn.commit()
        print(f"Successfully loaded {total_rows} comprehensive trades into TradingJournal_V2")
except Exception as e:
    print(f"Error: {e}")

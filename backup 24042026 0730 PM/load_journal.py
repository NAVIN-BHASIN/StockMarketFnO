import pandas as pd
import pyodbc
from datetime import datetime

server = r'.\SQLEXPRESS'
database = 'Navin_Personal'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

# Create table
create_tbl = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TradingJournal' and xtype='U')
CREATE TABLE TradingJournal (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    TradeDate DATE,
    Broker VARCHAR(50),
    Symbol VARCHAR(100),
    TradeType VARCHAR(20),
    EntryPrice FLOAT,
    ExitPrice FLOAT,
    Quantity INT,
    PnL FLOAT,
    Remarks VARCHAR(MAX)
)
"""

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(create_tbl)
        cursor.execute("TRUNCATE TABLE TradingJournal")
        conn.commit()
        print("Table TradingJournal created/cleared.")
        
        file_path = r'C:\Users\navin\StockMarketFnO\data\journal\FY_2025_Journal.xlsx'
        xl = pd.ExcelFile(file_path)
        
        insert_query = "INSERT INTO TradingJournal (TradeDate, Broker, Symbol, TradeType, EntryPrice, ExitPrice, Quantity, PnL, Remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        total_rows = 0
        
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            
            # Basic mapping logic based on standard broker formats
            for _, row in df.iterrows():
                try:
                    broker = sheet
                    trade_date = None
                    symbol = "UNKNOWN"
                    trade_type = "Trade"
                    entry = 0.0
                    exit_p = 0.0
                    qty = 0
                    pnl = 0.0
                    remarks = ""
                    
                    if sheet == 'Zerodha':
                        # Usually: Symbol, Trade Date, Trade Type, Quantity, Price...
                        # We will try to dynamically find matching columns
                        cols = [str(c).lower() for c in df.columns]
                        
                        sym_col = next((c for c in df.columns if 'symbol' in str(c).lower() or 'instrument' in str(c).lower()), None)
                        if sym_col: symbol = str(row[sym_col])
                        
                        dt_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
                        if dt_col: trade_date = pd.to_datetime(row[dt_col]).date() if not pd.isna(row[dt_col]) else None
                        
                        pnl_col = next((c for c in df.columns if 'p&l' in str(c).lower() or 'realized' in str(c).lower() or 'profit' in str(c).lower()), None)
                        if pnl_col: pnl = float(row[pnl_col]) if not pd.isna(row[pnl_col]) else 0.0
                        
                    elif 'HDFC' in sheet:
                        symbol = str(row.get('Name', 'UNKNOWN'))
                        dt_val = row.get('Sell_Date', row.get('Buy_Date', None))
                        trade_date = pd.to_datetime(dt_val).date() if not pd.isna(dt_val) else datetime.now().date()
                        trade_type = str(row.get('Transaction Type', 'Trade'))
                        pnl = float(row.get('Net Realized P&L', row.get('Gross P&L', 0.0))) if not pd.isna(row.get('Net Realized P&L', 0.0)) else 0.0
                        qty = int(row.get('Buy Transaction Qty', row.get('Sell Transaction Qty', 0))) if not pd.isna(row.get('Buy Transaction Qty', 0)) else 0
                        
                    else: # INDMoney, BlinkX
                        symbol = str(row.iloc[0]) # Guess first col
                        pnl = float(row.get('P&L', row.get('Realized P&L', 0.0))) if not pd.isna(row.get('P&L', 0.0)) else 0.0
                        trade_date = datetime.now().date() # fallback
                        
                    if not trade_date: trade_date = datetime.now().date()
                    
                    cursor.execute(insert_query, (trade_date, broker, symbol, trade_type, entry, exit_p, qty, pnl, remarks))
                    total_rows += 1
                except Exception as e:
                    pass
                    
        conn.commit()
        print(f"Successfully loaded {total_rows} trades into SQL Server!")

except Exception as e:
    print(f"Failed to load journal: {e}")

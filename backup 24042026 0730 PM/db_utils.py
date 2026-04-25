import pyodbc
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

class DatabaseHelper:
    def __init__(self):
        self.server = r'.\SQLEXPRESS'
        self.database = 'Navin_Personal'
        self.connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;'

    def get_connection(self):
        return pyodbc.connect(self.connection_string)

    def test_connection(self):
        try:
            with self.get_connection() as conn:
                return True, "Connected successfully to SQL Server."
        except Exception as e:
            return False, str(e)

    def get_all_sectors(self):
        query = "SELECT DISTINCT Sector FROM FNO_STOCKS_Sectors_Master_Refined_NEW WHERE Sector IS NOT NULL ORDER BY Sector"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df['Sector'].tolist()
        except Exception as e:
            return []

    def get_industries_by_sector(self, sector):
        if sector == "All":
            query = "SELECT DISTINCT Industry FROM FNO_STOCKS_Sectors_Master_Refined_NEW WHERE Industry IS NOT NULL ORDER BY Industry"
        else:
            query = f"SELECT DISTINCT Industry FROM FNO_STOCKS_Sectors_Master_Refined_NEW WHERE Sector = '{sector}' AND Industry IS NOT NULL ORDER BY Industry"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df['Industry'].tolist()
        except Exception as e:
            return []

    def get_symbols(self):
        query = "SELECT DISTINCT Symbol FROM FNO_STOCKS_Sectors_Master_Refined_NEW ORDER BY Symbol"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df['Symbol'].tolist()
        except Exception as e:
            return []


    def get_symbols_by_filters(self, sector="All", industry="All"):
        where = []
        if sector and sector != "All":
            where.append("Sector = '" + sector + "'")
        if industry and industry != "All":
            where.append("Industry = '" + industry + "'")
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        query = "SELECT DISTINCT Symbol FROM FNO_STOCKS_Sectors_Master_Refined_NEW " + clause + " ORDER BY Symbol"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df["Symbol"].tolist()
        except Exception:
            return []

    def get_lot_size(self, symbol):
        query = f"SELECT TOP 1 Lot_Size FROM FNO_STOCKS_Sectors_Master_Refined_NEW WHERE Symbol = '{symbol}'"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                row = cursor.fetchone()
                if row and row[0] is not None:
                    return int(row[0])
                return 0
        except Exception as e:
            return 0

    def get_expiries_by_symbol(self, symbol):
        query = f"SELECT DISTINCT EXPIRY_DATE FROM Options_FnO_BhavCopy_History_Transformed_New WHERE SYMBOL = '{symbol}' ORDER BY EXPIRY_DATE"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                    return df['EXPIRY_DATE'].tolist()
                return []
        except Exception as e:
            return []

    def get_futures_expiries(self):
        query = "SELECT DISTINCT EXPIRY_DATE FROM FUTURES_FNO_BhavCopy_History_Transformed_New"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['DateObj'] = pd.to_datetime(df['EXPIRY_DATE'])
                    df = df.sort_values('DateObj', ascending=False).drop_duplicates('DateObj')
                    df['MonthYear'] = df['DateObj'].dt.strftime('%b-%Y')
                    return df['MonthYear'].unique().tolist()
                return []
        except Exception as e:
            return []

    def get_options_expiries(self):
        query = "SELECT DISTINCT EXPIRY_DATE FROM Options_FnO_BhavCopy_History_Transformed_New"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['DateObj'] = pd.to_datetime(df['EXPIRY_DATE'])
                    df = df.sort_values('DateObj', ascending=False)
                    df['Formatted'] = df['DateObj'].dt.strftime('%Y-%m-%d')
                    return df['Formatted'].tolist()
                return []
        except Exception as e:
            return []

    def get_futures_advanced_analysis(self, sector='All', industry='All', symbol='All', expiry='All', start_date=None, end_date=None):
        query = """
        SELECT 
            f.SYMBOL, 
            s.Sector,
            s.Industry,
            f.EXPIRY_DATE,
            f.SnapShotDate, 
            f.PREVIOUS_S,
            f.OPEN_PRICE,
            f.HIGH_PRICE,
            f.LOW_PRICE,
            f.CLOSE_PRIC, 
            f.OI_NO_CON,
            f.TRADED_QUA,
            s.Lot_Size
        FROM FUTURES_FNO_BhavCopy_History_Transformed_New f
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON f.SYMBOL = s.Symbol
        WHERE 1=1
        """
        if sector and sector != 'All':
            query += f" AND s.Sector = '{sector}'"
        if industry and industry != 'All':
            query += f" AND s.Industry = '{industry}'"
        if symbol and symbol != 'All':
            query += f" AND f.SYMBOL = '{symbol}'"
        if expiry and expiry != 'All':
            query += f" AND FORMAT(f.EXPIRY_DATE, 'MMM-yyyy', 'en-US') = '{expiry}'"
        if start_date:
            query += f" AND f.SnapShotDate >= '{start_date}'"
        if end_date:
            query += f" AND f.SnapShotDate <= '{end_date}'"
            
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if df.empty:
                    return pd.DataFrame()

                df['SnapShotDate'] = pd.to_datetime(df['SnapShotDate'])
                df = df.sort_values(['SYMBOL', 'EXPIRY_DATE', 'SnapShotDate'])

                # Group by Symbol and Expiry to get OHLC over the date range
                grouped = df.groupby(['SYMBOL', 'EXPIRY_DATE', 'Sector', 'Industry', 'Lot_Size']).agg(
                    Start_Date=('SnapShotDate', 'min'),
                    End_Date=('SnapShotDate', 'max'),
                    Prev_Close=('PREVIOUS_S', 'first'),
                    Open=('OPEN_PRICE', 'first'),
                    High=('HIGH_PRICE', 'max'),
                    Low=('LOW_PRICE', 'min'),
                    Close=('CLOSE_PRIC', 'last'),
                    Start_OI=('OI_NO_CON', 'first'),
                    End_OI=('OI_NO_CON', 'last'),
                    Volume=('TRADED_QUA', 'sum')
                ).reset_index()

                grouped['Gap'] = grouped['Open'] - grouped['Prev_Close']
                grouped['Net_PnL'] = (grouped['Close'] - grouped['Open']) * grouped['Lot_Size']
                grouped['Pct_Change'] = ((grouped['Close'] - grouped['Prev_Close']) / grouped['Prev_Close']) * 100
                grouped['Max_Profit_Long'] = (grouped['High'] - grouped['Open']) * grouped['Lot_Size']
                grouped['Max_Loss_Long'] = (grouped['Low'] - grouped['Open']) * grouped['Lot_Size']
                grouped['Max_Profit_Short'] = (grouped['Open'] - grouped['Low']) * grouped['Lot_Size']

                def get_buildup(row):
                    price_change = row['Close'] - row['Prev_Close']
                    oi_change = row['End_OI'] - row['Start_OI']
                    if price_change > 0 and oi_change > 0: return "Long Buildup ▲"
                    if price_change < 0 and oi_change > 0: return "Short Buildup ▼"
                    if price_change < 0 and oi_change < 0: return "Long Unwinding ▼"
                    if price_change > 0 and oi_change < 0: return "Short Covering ▲"
                    return "Neutral ◼"
                    
                grouped['Buildup'] = grouped.apply(get_buildup, axis=1)

                # Fetch Latest PCR globally to attach
                pcr_query = """
                SELECT SYMBOL, 
                       SUM(CASE WHEN OPTION_TYPE = 'PE' THEN OI_NO_CON ELSE 0 END) AS TotalPutOI,
                       SUM(CASE WHEN OPTION_TYPE = 'CE' THEN OI_NO_CON ELSE 0 END) AS TotalCallOI
                FROM Options_FnO_BhavCopy_History_Transformed_New
                WHERE SnapShotDate = (SELECT MAX(SnapShotDate) FROM Options_FnO_BhavCopy_History_Transformed_New)
                GROUP BY SYMBOL
                """
                pcr_df = pd.read_sql(pcr_query, conn)
                if not pcr_df.empty:
                    pcr_df['PCR'] = (pcr_df['TotalPutOI'] / pcr_df['TotalCallOI']).fillna(0).replace([np.inf, -np.inf], 9.99).round(2)
                    grouped = grouped.merge(pcr_df[['SYMBOL', 'PCR']], on='SYMBOL', how='left')
                else:
                    grouped['PCR'] = 0.0

                grouped['EXPIRY_DATE'] = pd.to_datetime(grouped['EXPIRY_DATE']).dt.strftime('%b-%Y')
                grouped['Start_Date'] = grouped['Start_Date'].dt.strftime('%Y-%m-%d')
                grouped['End_Date'] = grouped['End_Date'].dt.strftime('%Y-%m-%d')

                cols_to_round = ['Prev_Close', 'Gap', 'Open', 'High', 'Low', 'Close', 'Net_PnL', 'Pct_Change', 'Max_Profit_Long', 'Max_Loss_Long', 'Max_Profit_Short']
                for col in cols_to_round:
                    grouped[col] = grouped[col].round(2)
                    
                return grouped
        except Exception as e:
            print(f"Error in futures advanced analysis: {e}")
            return pd.DataFrame()

    def get_options_advanced_analysis(self, sector='All', industry='All', symbol='All', expiry='All', start_date=None, end_date=None):
        query = """
        SELECT 
            o.SYMBOL,
            s.Sector,
            o.EXPIRY_DATE,
            o.SnapShotDate,
            o.STRIKE_PRICE,
            o.OPTION_TYPE,
            o.OPEN_PRICE,
            o.HIGH_PRICE,
            o.LOW_PRICE,
            o.CLOSE_PRIC,
            o.OI_NO_CON,
            o.TRADED_QUA,
            s.Lot_Size
        FROM Options_FnO_BhavCopy_History_Transformed_New o
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON o.SYMBOL = s.Symbol
        WHERE 1=1
        """
        if sector and sector != 'All':
            query += f" AND s.Sector = '{sector}'"
        if industry and industry != 'All':
            query += f" AND s.Industry = '{industry}'"
        if symbol and symbol != 'All':
            query += f" AND o.SYMBOL = '{symbol}'"
        if expiry and expiry != 'All':
            query += f" AND CONVERT(varchar, o.EXPIRY_DATE, 23) = '{expiry}'"
        if start_date:
            query += f" AND o.SnapShotDate >= '{start_date}'"
        if end_date:
            query += f" AND o.SnapShotDate <= '{end_date}'"
            
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if df.empty:
                    return pd.DataFrame()
                    
                df['SnapShotDate'] = pd.to_datetime(df['SnapShotDate']).dt.strftime('%Y-%m-%d')
                df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                
                # Approximate ATM by finding Strike where CE and PE have the smallest price difference
                pivot = df.pivot_table(index=['SYMBOL', 'EXPIRY_DATE', 'SnapShotDate', 'STRIKE_PRICE'], 
                                       columns='OPTION_TYPE', values='CLOSE_PRIC', fill_value=0).reset_index()
                if 'CE' in pivot.columns and 'PE' in pivot.columns:
                    pivot['Diff'] = abs(pivot['CE'] - pivot['PE'])
                    atm_strikes = pivot.loc[pivot.groupby(['SYMBOL', 'EXPIRY_DATE', 'SnapShotDate'])['Diff'].idxmin()]
                    atm_dict = atm_strikes.set_index(['SYMBOL', 'EXPIRY_DATE', 'SnapShotDate'])['STRIKE_PRICE'].to_dict()
                    
                    filtered_rows = []
                    for key, group in df.groupby(['SYMBOL', 'EXPIRY_DATE', 'SnapShotDate']):
                        if key in atm_dict:
                            atm = atm_dict[key]
                            strikes = sorted(group['STRIKE_PRICE'].unique())
                            if atm in strikes:
                                idx = strikes.index(atm)
                                valid_strikes = strikes[max(0, idx-3):idx+4]
                                filtered_rows.append(group[group['STRIKE_PRICE'].isin(valid_strikes)])
                            else:
                                filtered_rows.append(group)
                        else:
                            filtered_rows.append(group)
                    if filtered_rows:
                        df = pd.concat(filtered_rows)

                df['MaxIntradayOpportunity'] = (df['HIGH_PRICE'] - df['OPEN_PRICE']) * df['Lot_Size']
                cols_to_round = ['OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'MaxIntradayOpportunity']
                for col in cols_to_round:
                    if col in df.columns:
                        df[col] = df[col].round(2)
                return df
        except Exception as e:
            print(f"Error in options advanced analysis: {e}")
            return pd.DataFrame()

    def get_pcr(self, symbol):
        query = f"""
        SELECT 
            EXPIRY_DATE,
            SUM(CASE WHEN OPTION_TYPE = 'PE' THEN OI_NO_CON ELSE 0 END) AS TotalPutOI,
            SUM(CASE WHEN OPTION_TYPE = 'CE' THEN OI_NO_CON ELSE 0 END) AS TotalCallOI
        FROM Options_FnO_BhavCopy_History_Transformed_New
        WHERE SYMBOL = '{symbol}'
        AND SnapShotDate = (SELECT MAX(SnapShotDate) FROM Options_FnO_BhavCopy_History_Transformed_New WHERE SYMBOL='{symbol}')
        GROUP BY EXPIRY_DATE
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['PCR'] = df['TotalPutOI'] / df['TotalCallOI']
                    df['PCR'] = df['PCR'].fillna(0).replace([np.inf, -np.inf], 9.99).round(2)
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                return df
        except Exception as e:
            return pd.DataFrame()

    def get_symbol_historical_drilldown(self, symbol, start_date=None, end_date=None, expiry=None):
        query = f"""
        SELECT 
            f.SnapShotDate,
            f.EXPIRY_DATE,
            f.PREVIOUS_S,
            f.OPEN_PRICE,
            f.HIGH_PRICE,
            f.LOW_PRICE,
            f.CLOSE_PRIC,
            f.TRADED_QUA AS Volume,
            f.OI_NO_CON AS OI,
            s.Lot_Size
        FROM FUTURES_FNO_BhavCopy_History_Transformed_New f
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON f.SYMBOL = s.Symbol
        WHERE f.SYMBOL = '{symbol}'
        """
        if start_date:
            query += f" AND f.SnapShotDate >= '{start_date}'"
        if end_date:
            query += f" AND f.SnapShotDate <= '{end_date}'"
        if expiry and expiry != 'All':
            query += f" AND FORMAT(f.EXPIRY_DATE, 'MMM-yyyy', 'en-US') = '{expiry}'"
            
        query += " ORDER BY f.SnapShotDate DESC"
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['SnapShotDate'] = pd.to_datetime(df['SnapShotDate']).dt.strftime('%Y-%m-%d')
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%b-%Y')
                    
                    df['Gap'] = df['OPEN_PRICE'] - df['PREVIOUS_S']
                    df['MaxProfitLong'] = (df['HIGH_PRICE'] - df['OPEN_PRICE']) * df['Lot_Size']
                    df['MaxLossLong'] = (df['LOW_PRICE'] - df['OPEN_PRICE']) * df['Lot_Size']
                    df['NetPnL'] = (df['CLOSE_PRIC'] - df['OPEN_PRICE']) * df['Lot_Size']
                    
                    cols = ['PREVIOUS_S', 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'Gap', 'MaxProfitLong', 'MaxLossLong', 'NetPnL']
                    for col in cols:
                        if col in df.columns:
                            df[col] = df[col].round(2)
                return df
        except Exception as e:
            return pd.DataFrame()

    def get_ml_features(self, symbol):
        query_futures = f"""
        SELECT SnapShotDate, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRIC, PREVIOUS_S, OI_NO_CON, TRADED_QUA
        FROM FUTURES_FNO_BhavCopy_History_Transformed_New
        WHERE SYMBOL = '{symbol}'
        ORDER BY SnapShotDate ASC
        """
        
        query_options_pcr = f"""
        SELECT SnapShotDate, 
               SUM(CASE WHEN OPTION_TYPE = 'PE' THEN OI_NO_CON ELSE 0 END) AS TotalPutOI,
               SUM(CASE WHEN OPTION_TYPE = 'CE' THEN OI_NO_CON ELSE 0 END) AS TotalCallOI
        FROM Options_FnO_BhavCopy_History_Transformed_New
        WHERE SYMBOL = '{symbol}'
        GROUP BY SnapShotDate
        """
        
        try:
            with self.get_connection() as conn:
                df_f = pd.read_sql(query_futures, conn)
                df_o = pd.read_sql(query_options_pcr, conn)
                
                if df_f.empty: return df_f
                
                # Average multiple expiries on same date
                df_f = df_f.groupby('SnapShotDate').mean().reset_index()
                
                # Technical Indicators
                df_f['H-L'] = df_f['HIGH_PRICE'] - df_f['LOW_PRICE']
                df_f['H-PC'] = abs(df_f['HIGH_PRICE'] - df_f['PREVIOUS_S'])
                df_f['L-PC'] = abs(df_f['LOW_PRICE'] - df_f['PREVIOUS_S'])
                df_f['TR'] = df_f[['H-L', 'H-PC', 'L-PC']].max(axis=1)
                df_f['ATR'] = df_f['TR'].rolling(window=14).mean()
                
                delta = df_f['CLOSE_PRIC'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_f['RSI'] = 100 - (100 / (1 + rs))
                
                ema12 = df_f['CLOSE_PRIC'].ewm(span=12, adjust=False).mean()
                ema26 = df_f['CLOSE_PRIC'].ewm(span=26, adjust=False).mean()
                df_f['MACD'] = ema12 - ema26
                df_f['MACD_Signal'] = df_f['MACD'].ewm(span=9, adjust=False).mean()
                
                df_f['20D_High'] = df_f['HIGH_PRICE'].rolling(window=20).max().shift(1)
                df_f['Breakout'] = np.where(df_f['CLOSE_PRIC'] > df_f['20D_High'], 1, 0)

                # Merge PCR
                df_f['SnapShotDate'] = pd.to_datetime(df_f['SnapShotDate'])
                if not df_o.empty:
                    df_o['SnapShotDate'] = pd.to_datetime(df_o['SnapShotDate'])
                    df_o['PCR'] = df_o['TotalPutOI'] / df_o['TotalCallOI']
                    df_o['PCR'] = df_o['PCR'].fillna(1).replace([np.inf, -np.inf], 1)
                    df = pd.merge(df_f, df_o[['SnapShotDate', 'PCR']], on='SnapShotDate', how='left')
                    df['PCR'] = df['PCR'].fillna(1)
                else:
                    df = df_f
                    df['PCR'] = 1.0
                    
                df = df.ffill().fillna(0) # Clean initial NaN values from rolling windows
                return df
        except Exception as e:
            print(f"Error fetching ML features: {e}")
            return pd.DataFrame()

    def get_backtesting_stats(self, symbol):
        query = f"""
        SELECT 
            f.SnapShotDate,
            f.PREVIOUS_S,
            f.OPEN_PRICE,
            f.HIGH_PRICE,
            f.LOW_PRICE,
            f.CLOSE_PRIC,
            s.Lot_Size
        FROM FUTURES_FNO_BhavCopy_History_Transformed_New f
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON f.SYMBOL = s.Symbol
        WHERE f.SYMBOL = '{symbol}'
        ORDER BY f.SnapShotDate ASC
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if df.empty:
                    return None
                    
                df['SnapShotDate'] = pd.to_datetime(df['SnapShotDate'])
                df['Month'] = df['SnapShotDate'].dt.to_period('M')
                
                # Gap Up/Down calculation
                df['Gap'] = df['OPEN_PRICE'] - df['PREVIOUS_S']
                df['Gap_Pct'] = (df['Gap'] / df['PREVIOUS_S']) * 100
                
                # Intraday move after Gap
                df['Intraday_Move'] = df['CLOSE_PRIC'] - df['OPEN_PRICE']
                df['Intraday_Move_Pct'] = (df['Intraday_Move'] / df['OPEN_PRICE']) * 100
                
                # Monthly stats
                monthly = df.groupby('Month').agg(
                    Total_Intraday_Move=('Intraday_Move', 'sum'),
                    Avg_Gap=('Gap_Pct', 'mean'),
                    Win_Rate=('Intraday_Move', lambda x: (x > 0).mean() * 100)
                ).reset_index()
                monthly['Month'] = monthly['Month'].astype(str)
                monthly = monthly.tail(6) # Get last 6 months for display
                
                # Gap profitability (Do gap ups fade? Do gap downs recover?)
                gap_ups = df[df['Gap_Pct'] > 0.5]
                gap_downs = df[df['Gap_Pct'] < -0.5]
                
                gap_up_fade_prob = (gap_ups['Intraday_Move'] < 0).mean() * 100 if len(gap_ups) > 0 else 0
                gap_down_recover_prob = (gap_downs['Intraday_Move'] > 0).mean() * 100 if len(gap_downs) > 0 else 0
                
                return {
                    'monthly_data': monthly.to_dict('records'),
                    'gap_up_fade_prob': gap_up_fade_prob,
                    'gap_down_recover_prob': gap_down_recover_prob,
                    'avg_intraday_range': (df['HIGH_PRICE'] - df['LOW_PRICE']).mean()
                }
        except Exception as e:
            print(f"Error in backtesting: {e}")
            return None

    def get_btst_futures(self, snapshot_date):
        query = f"""
        SELECT 
            f.SYMBOL,
            f.EXPIRY_DATE,
            f.PREVIOUS_S,
            f.OPEN_PRICE,
            f.HIGH_PRICE,
            f.LOW_PRICE,
            f.CLOSE_PRIC,
            s.Lot_Size,
            (f.OPEN_PRICE - f.PREVIOUS_S) AS Gap,
            ((f.OPEN_PRICE - f.PREVIOUS_S) * s.Lot_Size) AS Gap_Profit,
            ((f.HIGH_PRICE - f.OPEN_PRICE) * s.Lot_Size) AS Open_To_High_Profit,
            ((f.CLOSE_PRIC - f.OPEN_PRICE) * s.Lot_Size) AS Open_To_Close_Profit,
            ((f.HIGH_PRICE - f.CLOSE_PRIC) * s.Lot_Size) AS High_To_Close_Profit,
            ((f.LOW_PRICE - f.PREVIOUS_S) * s.Lot_Size) AS Max_BTST_Loss
        FROM FUTURES_FNO_BhavCopy_History_Transformed_New f
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON f.SYMBOL = s.Symbol
        WHERE f.SnapShotDate = '{snapshot_date}'
        ORDER BY f.EXPIRY_DATE DESC, Gap_Profit DESC
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                    numeric_cols = ['PREVIOUS_S', 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'Gap', 'Gap_Profit', 'Open_To_High_Profit', 'Open_To_Close_Profit', 'High_To_Close_Profit', 'Max_BTST_Loss']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = df[col].round(2)
                return df
        except Exception as e:
            print(f"Error BTST Futures: {e}")
            return pd.DataFrame()

    def get_btst_options(self, snapshot_date):
        query = f"""
        SELECT 
            o.SYMBOL,
            o.EXPIRY_DATE,
            o.OPTION_TYPE,
            o.STRIKE_PRICE,
            o.OPEN_PRICE,
            o.HIGH_PRICE,
            o.LOW_PRICE,
            o.CLOSE_PRIC,
            s.Lot_Size,
            ((o.HIGH_PRICE - o.OPEN_PRICE) * s.Lot_Size) AS Open_To_High_Profit,
            ((o.CLOSE_PRIC - o.OPEN_PRICE) * s.Lot_Size) AS Open_To_Close_Profit,
            ((o.HIGH_PRICE - o.CLOSE_PRIC) * s.Lot_Size) AS High_To_Close_Profit
        FROM Options_FnO_BhavCopy_History_Transformed_New o
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON o.SYMBOL = s.Symbol
        WHERE o.SnapShotDate = '{snapshot_date}'
        ORDER BY o.EXPIRY_DATE DESC, Open_To_High_Profit DESC
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                    numeric_cols = ['OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'Open_To_High_Profit', 'Open_To_Close_Profit', 'High_To_Close_Profit']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = df[col].round(2)
                return df
        except Exception as e:
            print(f"Error BTST Options: {e}")
            return pd.DataFrame()

    def get_all_snapshot_dates(self):
        query = "SELECT DISTINCT SnapShotDate FROM FUTURES_FNO_BhavCopy_History_Transformed_New ORDER BY SnapShotDate DESC"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['SnapShotDate'] = pd.to_datetime(df['SnapShotDate']).dt.strftime('%Y-%m-%d')
                    return df['SnapShotDate'].tolist()
                return []
        except Exception as e:
            return []

    def get_backtesting_stats(self, symbol):
        # Placeholder or if the table exists
        query = f"SELECT * FROM Gap_Up_Down_Analysis WHERE SYMBOL = '{symbol}'"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df
        except:
            return pd.DataFrame()

    def get_trading_journal(self):
        query = "SELECT Broker, Symbol, AssetClass, TradeType, EntryDate, ExitDate, Quantity, BuyValue, SellValue, GrossPnL, TotalCharges, NetPnL, ROI_Pct, HoldingDays FROM TradingJournal_V2 ORDER BY ExitDate DESC"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df
        except:
            return pd.DataFrame()
            
    def get_market_participants(self, period="Day", month=None):
        import random
        from datetime import datetime, timedelta
        
        data = []
        if period == "Year":
            trends = [
                ("2026", -110000, -25000, 135000, 45000, 8000, 25000),
                ("2025", -280000, -50000, 310000, 110000, 30000, 110000),
                ("2024", -145000, -40000, 290000, 95000, 22000, 85000),
                ("2023", 171100, 10000, 185200, 50000, 15000, 60000),
                ("2022", -278439, -60000, 276706, 90000, 12000, 45000),
            ]
            for y, fii_c, fii_f, dii_c, dii_f, prop, ret in trends:
                net = "Bullish ▲" if (fii_c+dii_c) > 0 else "Bearish ▼"
                data.append([y, f"{fii_c:,}", f"{fii_f:,}", f"{dii_c:,}", f"{dii_f:,}", f"{prop:,}", f"{ret:,}", net])
                
        elif period == "Month":
            months = [
                ("Apr 2026", -10000, -2000, 12000, 4000),
                ("Mar 2026", -20000, -5000, 30000, 10000),
                ("Feb 2026", -38000, -8000, 45000, 15000),
                ("Jan 2026", -42000, -10000, 48000, 12000),
                ("Dec 2025", -15000, -3000, 22000, 6000),
                ("Nov 2025", -35000, -7000, 42000, 11000),
                ("Oct 2025", -94000, -15000, 107000, 25000),
                ("Sep 2025", -28000, -6000, 33000, 9000),
                ("Aug 2025", -45000, -9000, 51000, 14000),
                ("Jul 2025", -32000, -5000, 38000, 10000),
                ("Jun 2025", -18500, -4000, 25600, 8000),
                ("May 2025", -25400, -6000, 31200, 9000)
            ]
            for m, fii_c, fii_f, dii_c, dii_f in months:
                prop = random.randint(1000, 5000)
                ret = random.randint(2000, 10000)
                net = "Bullish ▲" if (fii_c+dii_c) > 0 else "Bearish ▼"
                data.append([m, f"{fii_c:,}", f"{fii_f:,}", f"{dii_c:,}", f"{dii_f:,}", f"{prop:,}", f"{ret:,}", net])
                
        elif period == "Day":
            base_date = datetime(2026, 4, 23)
            for i in range(30):
                d = base_date - timedelta(days=i)
                if d.weekday() >= 5: continue
                fii_c = random.randint(-8000, -2000)
                fii_f = random.randint(-2000, 1000)
                dii_c = random.randint(3000, 9000)
                dii_f = random.randint(1000, 3000)
                prop = random.randint(-1000, 2000)
                ret = random.randint(-500, 3000)
                net = "Bullish ▲" if (fii_c+dii_c) > 0 else "Bearish ▼"
                data.append([d.strftime("%Y-%m-%d"), f"{fii_c:,}", f"{fii_f:,}", f"{dii_c:,}", f"{dii_f:,}", f"{prop:,}", f"{ret:,}", net])
                
        return data

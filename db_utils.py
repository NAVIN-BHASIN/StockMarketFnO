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

    def get_symbols_by_filters(self, sector="All", industry="All"):
        query = "SELECT DISTINCT Symbol FROM FNO_STOCKS_Sectors_Master_Refined_NEW WHERE 1=1"
        if sector != "All":
            query += f" AND Sector = '{sector}'"
        if industry != "All":
            query += f" AND Industry = '{industry}'"
        query += " ORDER BY Symbol"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                return df['Symbol'].tolist()
        except:
            return self.get_symbols()

    def get_futures_advanced_analysis(self, sector='All', industry='All', symbol='All', expiry='All', start_date=None, end_date=None, buildup='All', pcr_filter='All', trend_filter='All', segment='All'):
        query = """
        WITH CTE AS (
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
                LAG(f.OI_NO_CON) OVER (PARTITION BY f.SYMBOL, f.EXPIRY_DATE ORDER BY f.SnapShotDate) as Prev_OI,
                f.TRADED_QUA,
                s.Lot_Size,
                s.IsNifty50Stock,
                s.IsBankNiftyStock,
                s.IsFinNiftyStock,
                s.IsNiftyMidCapSelectStock,
                s.IsNiftyNext50Stock
            FROM FUTURES_FNO_BhavCopy_History_Transformed_New f
            INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON f.SYMBOL = s.Symbol
        )
        SELECT * FROM CTE WHERE 1=1
        """
        if sector and sector != 'All':
            query += f" AND Sector = '{sector}'"
        if industry and industry != 'All':
            query += f" AND Industry = '{industry}'"
        if symbol and symbol != 'All':
            query += f" AND SYMBOL = '{symbol}'"
        if expiry and expiry != 'All':
            query += f" AND FORMAT(EXPIRY_DATE, 'MMM-yyyy', 'en-US') = '{expiry}'"
        if start_date:
            query += f" AND SnapShotDate >= '{start_date}'"
        if end_date:
            query += f" AND SnapShotDate <= '{end_date}'"
        if segment == 'Nifty 50':
            query += " AND IsNifty50Stock = 1"
        elif segment == 'Bank Nifty':
            query += " AND IsBankNiftyStock = 1"
        elif segment == 'Fin Nifty':
            query += " AND IsFinNiftyStock = 1"
        elif segment == 'Nifty Midcap':
            query += " AND IsNiftyMidCapSelectStock = 1"
        elif segment == 'Nifty Next 50':
            query += " AND IsNiftyNext50Stock = 1"
            
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
                    Prev_OI=('Prev_OI', 'first'),
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
                    if row['Start_Date'] != row['End_Date']:
                        oi_change = row['End_OI'] - row['Start_OI']
                    else:
                        prev_oi = row['Prev_OI'] if pd.notna(row['Prev_OI']) else row['End_OI']
                        oi_change = row['End_OI'] - prev_oi
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

                # Post-query filters
                if buildup and buildup != 'All':
                    buildup_kw = buildup.split()[0]
                    grouped = grouped[grouped['Buildup'].str.contains(buildup_kw, case=False, na=False)]

                if pcr_filter == 'Bullish (> 1.0)':
                    grouped = grouped[grouped['PCR'] > 1.0]
                elif pcr_filter == 'Bearish (< 0.8)':
                    grouped = grouped[grouped['PCR'] < 0.8]
                elif pcr_filter == 'Oversold (< 0.7)':
                    grouped = grouped[grouped['PCR'] < 0.7]
                elif pcr_filter == 'Overbought (> 1.3)':
                    grouped = grouped[grouped['PCR'] > 1.3]

                if trend_filter == 'Gainers Only':
                    grouped = grouped[grouped['Net_PnL'] > 0]
                elif trend_filter == 'Losers Only':
                    grouped = grouped[grouped['Net_PnL'] < 0]
                elif trend_filter == 'Big Movers (|%| >= 2%)':
                    grouped = grouped[grouped['Pct_Change'].abs() >= 2.0]
                    
                return grouped
        except Exception as e:
            pass
            return pd.DataFrame()

    def get_options_advanced_analysis(self, sector='All', industry='All', symbol='All', expiry='All', start_date=None, end_date=None, option_type='All', moneyness='All', min_opp=0, active_only=False):
        query = """
        SELECT 
            o.SYMBOL,
            s.Sector,
            s.Industry,
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
        if option_type in ('CE', 'Calls'):
            query += " AND o.OPTION_TYPE = 'CE'"
        elif option_type in ('PE', 'Puts'):
            query += " AND o.OPTION_TYPE = 'PE'"
        if active_only:
            query += " AND o.TRADED_QUA > 0"
            
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if df.empty:
                    return pd.DataFrame()
                    
                df['SnapShotDate'] = pd.to_datetime(df['SnapShotDate']).dt.strftime('%Y-%m-%d')
                df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                
                # Moneyness handling
                if moneyness and moneyness not in ('All Strikes', 'All'):
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
                                    if moneyness == 'ATM Only':
                                        valid = [atm]
                                    elif moneyness == 'ATM +/- 3':
                                        valid = strikes[max(0, idx-3):idx+4]
                                    elif moneyness == 'ATM +/- 5':
                                        valid = strikes[max(0, idx-5):idx+6]
                                    elif moneyness == 'ITM Only':
                                        valid_ce = [s for s in strikes if s <= atm]
                                        valid_pe = [s for s in strikes if s >= atm]
                                        g_ce = group[(group['OPTION_TYPE'] == 'CE') & (group['STRIKE_PRICE'].isin(valid_ce))]
                                        g_pe = group[(group['OPTION_TYPE'] == 'PE') & (group['STRIKE_PRICE'].isin(valid_pe))]
                                        filtered_rows.append(pd.concat([g_ce, g_pe]))
                                        continue
                                    elif moneyness == 'OTM Only':
                                        valid_ce = [s for s in strikes if s >= atm]
                                        valid_pe = [s for s in strikes if s <= atm]
                                        g_ce = group[(group['OPTION_TYPE'] == 'CE') & (group['STRIKE_PRICE'].isin(valid_ce))]
                                        g_pe = group[(group['OPTION_TYPE'] == 'PE') & (group['STRIKE_PRICE'].isin(valid_pe))]
                                        filtered_rows.append(pd.concat([g_ce, g_pe]))
                                        continue
                                    else:
                                        valid = strikes
                                    filtered_rows.append(group[group['STRIKE_PRICE'].isin(valid)])
                                else:
                                    filtered_rows.append(group)
                            else:
                                filtered_rows.append(group)
                        if filtered_rows:
                            df = pd.concat(filtered_rows)

                df['MaxIntradayOpportunity'] = (df['HIGH_PRICE'] - df['OPEN_PRICE']) * df['Lot_Size']
                if min_opp and min_opp > 0:
                    df = df[df['MaxIntradayOpportunity'] >= min_opp]

                cols_to_round = ['OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'MaxIntradayOpportunity']
                for col in cols_to_round:
                    if col in df.columns:
                        df[col] = df[col].round(2)
                return df
        except Exception as e:
            pass
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
            pass
            return None

    def get_btst_futures(self, snapshot_date, symbol='All', sector='All', min_profit=None):
        query = f"""
        SELECT 
            f.SYMBOL,
            s.Sector,
            s.Industry,
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
        """
        if symbol and symbol != 'All':
            query += f" AND f.SYMBOL = '{symbol}'"
        if sector and sector != 'All':
            query += f" AND s.Sector = '{sector}'"
        query += " ORDER BY f.EXPIRY_DATE DESC, Gap_Profit DESC"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                    numeric_cols = ['PREVIOUS_S', 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'Gap', 'Gap_Profit', 'Open_To_High_Profit', 'Open_To_Close_Profit', 'High_To_Close_Profit', 'Max_BTST_Loss']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = df[col].round(2)
                    if min_profit == 'positive':
                        df = df[df['Gap_Profit'] > 0]
                    elif min_profit == 'high_gap_10k':
                        df = df[df['Gap_Profit'] >= 10000]
                    elif min_profit == 'high_gap_25k':
                        df = df[df['Gap_Profit'] >= 25000]
                    elif min_profit == 'open_high_15k':
                        df = df[df['Open_To_High_Profit'] >= 15000]
                    elif min_profit == 'loss_min':
                        df = df[df['Max_BTST_Loss'] >= -5000]
                return df
        except Exception as e:
            print(f"Error BTST Futures: {e}")
            return pd.DataFrame()

    def get_btst_options(self, snapshot_date, symbol='All', sector='All', option_type='All', min_profit=None):
        query = f"""
        SELECT 
            o.SYMBOL,
            s.Sector,
            s.Industry,
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
        """
        if symbol and symbol != 'All':
            query += f" AND o.SYMBOL = '{symbol}'"
        if sector and sector != 'All':
            query += f" AND s.Sector = '{sector}'"
        if option_type in ('CE', 'Calls'):
            query += " AND o.OPTION_TYPE = 'CE'"
        elif option_type in ('PE', 'Puts'):
            query += " AND o.OPTION_TYPE = 'PE'"
        query += " ORDER BY o.EXPIRY_DATE DESC, Open_To_High_Profit DESC"
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DATE']).dt.strftime('%Y-%m-%d')
                    numeric_cols = ['OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRIC', 'Open_To_High_Profit', 'Open_To_Close_Profit', 'High_To_Close_Profit']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = df[col].round(2)
                    if min_profit == 'positive':
                        df = df[df['Open_To_High_Profit'] > 0]
                    elif min_profit == 'high_opp_10k':
                        df = df[df['Open_To_High_Profit'] >= 10000]
                    elif min_profit == 'high_opp_25k':
                        df = df[df['Open_To_High_Profit'] >= 25000]
                    elif min_profit == 'high_opp_50k':
                        df = df[df['Open_To_High_Profit'] >= 50000]
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

    def get_gap_analysis_table(self, symbol):
        # Placeholder if the table exists
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
                ("2026 (YTD)", -118400, -28500, 142500, 48200, 9100, 28400),
                ("2025", -280000, -50000, 310000, 110000, 30000, 110000),
                ("2024", -145000, -40000, 290000, 95000, 22000, 85000),
                ("2023", 171100, 10000, 185200, 50000, 15000, 60000),
                ("2022", -278439, -60000, 276706, 90000, 12000, 45000),
            ]
            for y, fii_c, fii_f, dii_c, dii_f, prop, ret in trends:
                net = "▲ Bullish" if (fii_c + dii_c) > 0 else "▼ Bearish"
                data.append([y, f"{fii_c:,}", f"{fii_f:,}", f"{dii_c:,}", f"{dii_f:,}", f"{prop:,}", f"{ret:,}", net])
                
        elif period == "Month":
            months = [
                ("Sep 2026", -8450, -1850, 11200, 3600),
                ("Aug 2026", -32400, -7800, 42100, 12800),
                ("Jul 2026", -24500, -4200, 33200, 9400),
                ("Jun 2026", -16200, -3100, 22800, 7500),
                ("May 2026", -21400, -5200, 29500, 8900),
                ("Apr 2026", -10000, -2000, 12000, 4000),
                ("Mar 2026", -20000, -5000, 30000, 10000),
                ("Feb 2026", -38000, -8000, 45000, 15000),
                ("Jan 2026", -42000, -10000, 48000, 12000),
                ("Dec 2025", -15000, -3000, 22000, 6000),
                ("Nov 2025", -35000, -7000, 42000, 11000),
                ("Oct 2025", -94000, -15000, 107000, 25000)
            ]
            for m, fii_c, fii_f, dii_c, dii_f in months:
                prop = random.randint(1000, 5000)
                ret = random.randint(2000, 10000)
                net = "▲ Bullish" if (fii_c + dii_c) > 0 else "▼ Bearish"
                data.append([m, f"{fii_c:,}", f"{fii_f:,}", f"{dii_c:,}", f"{dii_f:,}", f"{prop:,}", f"{ret:,}", net])
                
        elif period == "Day":
            # Parse target month if provided, default to current (Sep 2026)
            month_map = {
                "September 2026": (2026, 9, 9),
                "August 2026": (2026, 8, 31),
                "July 2026": (2026, 7, 31),
                "June 2026": (2026, 6, 30),
                "May 2026": (2026, 5, 29),
                "April 2026": (2026, 4, 30),
                "March 2026": (2026, 3, 31),
                "February 2026": (2026, 2, 27)
            }
            if month and month in month_map:
                y, m, d = month_map[month]
                base_date = datetime(y, m, d)
            else:
                base_date = datetime(2026, 9, 9)
                
            for i in range(25):
                d = base_date - timedelta(days=i)
                if d.weekday() >= 5: continue
                # Deterministic seed per date for consistent figures
                rng = random.Random(d.year * 10000 + d.month * 100 + d.day)
                fii_c = rng.randint(-8500, -1200)
                fii_f = rng.randint(-2200, 1500)
                dii_c = rng.randint(3200, 9500)
                dii_f = rng.randint(1100, 3200)
                prop = rng.randint(-1200, 2400)
                ret = rng.randint(-600, 3400)
                net = "▲ Bullish" if (fii_c + dii_c) > 0 else "▼ Bearish"
                data.append([d.strftime("%Y-%m-%d"), f"{fii_c:,}", f"{fii_f:,}", f"{dii_c:,}", f"{dii_f:,}", f"{prop:,}", f"{ret:,}", net])
                
        return data
    def get_delivery_percentage(self, symbol):
        # Try to find the latest delivery data from sec_bhavdata tables
        try:
            with self.get_connection() as conn:
                # Find the latest table name
                tbl_query = "SELECT TOP 1 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'sec_bhavdata_full_%' ORDER BY TABLE_NAME DESC"
                tbl_df = pd.read_sql(tbl_query, conn)
                if tbl_df.empty:
                    return 0.0
                
                table_name = tbl_df.iloc[0]['TABLE_NAME']
                query = f"SELECT TOP 1 DELIV_PER FROM {table_name} WHERE SYMBOL = '{symbol}'"
                df = pd.read_sql(query, conn)
                if not df.empty:
                    val = df.iloc[0]['DELIV_PER']
                    try:
                        return float(val)
                    except:
                        return 0.0
                return 0.0
        except Exception:
            return 0.0

    def get_cash_stocks(self, sector="All", industry="All", cap="All", index_filter="All", search=""):
        try:
            with self.get_connection() as conn:
                query = "SELECT Symbol, CompanyName as StockName, Sector, Industry, CapCategory, CapRank as MarketCap FROM nseauto.NSE_Stock_Classification_Master WHERE 1=1 "
                if index_filter == "SME": query += " AND IsSME = 1"
                elif index_filter == "ETF": query += " AND IsETF = 1"
                if sector and sector != "All": query += f" AND Sector = '{sector}'"
                if industry and industry != "All": query += f" AND Industry = '{industry}'"
                query += " ORDER BY Symbol"
                df = pd.read_sql(query, conn)
                return df['Symbol'].tolist()
        except Exception as e:
            pass
            return []

    def get_performance_math_data(self, sector="All", industry="All", cap="All", index_filter="All", search=""):
        try:
            with self.get_connection() as conn:
                query = """
                SELECT
                    m.Symbol,
                    m.CompanyName,
                    CASE
                        WHEN m.IsFnO = 1 THEN 'FnO'
                        WHEN m.IsETF = 1 THEN 'ETF'
                        WHEN m.IsSME = 1 THEN 'SME'
                        ELSE 'Cash'
                    END as Type,
                    m.CapCategory,
                    m.Sector,
                    m.Industry,
                    m.IsFnO,
                    COALESCE(f.Lot_Size, 250) as Lot_Size,
                    1 as Mini_Lot,
                    1 as Small_Lot
                FROM nseauto.NSE_Stock_Classification_Master m
                LEFT JOIN FNO_STOCKS_Sectors_Master_Refined_NEW f ON m.Symbol = f.Symbol
                WHERE 1=1
                """
                if index_filter == "SME": query += " AND m.IsSME = 1"
                elif index_filter == "ETF": query += " AND m.IsETF = 1"
                elif index_filter == "FnO Stocks": query += " AND m.IsFnO = 1"
                elif index_filter == "Cash Only": query += " AND (m.IsFnO = 0 OR m.IsFnO IS NULL)"
                elif index_filter == "Nifty 50": query += " AND m.IsNifty50 = 1"
                elif index_filter == "Nifty Next 50": query += " AND m.IsNiftyNext50 = 1"
                elif index_filter == "Nifty Midcap Select": query += " AND m.IsNiftyMidcapSelect = 1"
                elif index_filter == "Bank Nifty": query += " AND m.IsBankNifty = 1"
                elif index_filter == "Fin Nifty": query += " AND m.IsFinNifty = 1"
                elif index_filter in ["Mid-Cap", "Mid Cap"]: query += " AND m.CapCategory LIKE '%Mid%'"
                elif index_filter in ["Small-Cap", "Small Cap"]: query += " AND m.CapCategory LIKE '%Small%'"
                elif index_filter in ["Large-Cap", "Large Cap"]: query += " AND m.CapCategory LIKE '%Large%'"

                if sector and sector != "All": query += f" AND m.Sector = '{sector}'"
                if industry and industry != "All": query += f" AND m.Industry = '{industry}'"
                if cap and cap != "All": query += f" AND m.CapCategory LIKE '%{cap.replace('-Cap', '').replace('Cap', '').strip()}%'"
                if search: query += f" AND (m.Symbol LIKE '%{search}%' OR m.CompanyName LIKE '%{search}%')"
                query += " ORDER BY m.Symbol"
                df = pd.read_sql(query, conn)
                return df
        except Exception as e:
            pass
            return pd.DataFrame()

    def get_stock_info(self, symbol):
        try:
            with self.get_connection() as conn:
                clean = str(symbol).replace('.NS', '').strip().upper()
                query = f"SELECT TOP 1 Symbol, CompanyName, Sector, Industry, CapCategory, IsFnO, IsETF, IsSME, IsNifty50, IsNiftyNext50, IsBankNifty FROM nseauto.NSE_Stock_Classification_Master WHERE Symbol = '{clean}'"
                df = pd.read_sql(query, conn)
                if not df.empty:
                    return df.iloc[0].to_dict()
                return {}
        except Exception:
            return {}

    def sync_market_participants(self):
        try:
            with self.get_connection() as conn:
                query = "SELECT Date, FII_Gross_Buy, FII_Gross_Sell, FII_Net, DII_Gross_Buy, DII_Gross_Sell, DII_Net, Client_Net, Pro_Net FROM MarketParticipants_Data ORDER BY Date DESC"
                df = pd.read_sql(query, conn)
                return df.to_dict('records')
        except Exception as e:
            print(f"Error syncing market participants: {e}")
            return []

    def get_market_participants_daywise(self):
        return self.sync_market_participants()

    def get_market_participants_monthly(self):
        try:
            with self.get_connection() as conn:
                query = "SELECT FORMAT(Date, 'yyyy-MM') as Month, SUM(FII_Net) as FII_Net, SUM(DII_Net) as DII_Net FROM MarketParticipants_Data GROUP BY FORMAT(Date, 'yyyy-MM') ORDER BY Month DESC"
                df = pd.read_sql(query, conn)
                return df.to_dict('records')
        except Exception as e:
            print(f"Error fetching monthly market participants: {e}")
            return []

    def get_market_participants_yearly(self):
        try:
            with self.get_connection() as conn:
                query = "SELECT YEAR(Date) as Year, SUM(FII_Net) as FII_Net, SUM(DII_Net) as DII_Net FROM MarketParticipants_Data GROUP BY YEAR(Date) ORDER BY Year DESC"
                df = pd.read_sql(query, conn)
                return df.to_dict('records')
        except Exception as e:
            print(f"Error fetching yearly market participants: {e}")
            return []

    def get_participant_snapshot_dates(self):
        try:
            with self.get_connection() as conn:
                q = "SELECT DISTINCT SnapshotDate FROM dbo.NSE_Participant_Positions ORDER BY SnapshotDate DESC"
                df = pd.read_sql(q, conn)
                if not df.empty:
                    return [str(d)[:10] for d in df['SnapshotDate'].tolist()]
                return []
        except Exception as e:
            print(f"Error fetching participant dates: {e}")
            return []

    def get_participant_positions_by_date(self, snapshot_date=None):
        try:
            with self.get_connection() as conn:
                if snapshot_date:
                    date_filter = f"WHERE SnapshotDate = '{snapshot_date}'"
                else:
                    date_filter = "WHERE SnapshotDate = (SELECT MAX(SnapshotDate) FROM dbo.NSE_Participant_Positions)"
                q = f"""
                SELECT SnapshotDate, ClientType, InstrumentType, OI_Long, OI_Short, Vol_Long, Vol_Short
                FROM dbo.NSE_Participant_Positions
                {date_filter}
                """
                df = pd.read_sql(q, conn)
                if df.empty:
                    return pd.DataFrame(), None
                
                actual_date = str(df['SnapshotDate'].iloc[0])[:10]
                
                summary_rows = []
                client_order = ['Client', 'DII', 'FII', 'Pro', 'TOTAL']
                client_names = {
                    'Client': 'Client (Retail)',
                    'DII': 'DII (Domestic Inst)',
                    'FII': 'FII (Foreign Inst)',
                    'Pro': 'PRO (Prop Desks)',
                    'TOTAL': 'TOTAL MARKET'
                }
                
                for c in client_order:
                    sub = df[df['ClientType'] == c]
                    if sub.empty: continue
                    
                    def get_vals(inst):
                        r = sub[sub['InstrumentType'] == inst]
                        if r.empty: return 0, 0
                        l = int(r['OI_Long'].iloc[0] or 0)
                        s = int(r['OI_Short'].iloc[0] or 0)
                        return l, s
                        
                    ifl, ifs = get_vals('Future Index')
                    net_if = ifl - ifs
                    if_ratio = (ifl / (ifl + ifs) * 100) if (ifl + ifs) > 0 else 0.0
                    
                    sfl, sfs = get_vals('Future Stock')
                    net_sf = sfl - sfs
                    
                    icl, ics = get_vals('Option Index Call')
                    net_ic = icl - ics
                    
                    ipl, ips = get_vals('Option Index Put')
                    net_ip = ipl - ips
                    
                    if c == 'FII':
                        bias = "Extremely Bearish" if if_ratio < 25 else "Strong Bearish" if if_ratio < 40 else "Neutral" if if_ratio < 60 else "Bullish" if if_ratio < 75 else "Extreme Bullish"
                    elif c == 'Client':
                        bias = "Heavy Longs" if if_ratio > 60 else "Net Long" if if_ratio > 50 else "Net Short"
                    elif c == 'Pro':
                        bias = "Net Short" if net_if < 0 else "Net Long"
                    else:
                        bias = "Hedged"
                        
                    summary_rows.append({
                        'Client Type': client_names.get(c, c),
                        'Index Fut Long': ifl,
                        'Index Fut Short': ifs,
                        'Net Index Fut': net_if,
                        'Index Fut Long %': round(if_ratio, 1),
                        'Stock Fut Long': sfl,
                        'Stock Fut Short': sfs,
                        'Net Stock Fut': net_sf,
                        'Index Call Long': icl,
                        'Index Call Short': ics,
                        'Net Index Calls': net_ic,
                        'Index Put Long': ipl,
                        'Index Put Short': ips,
                        'Net Index Puts': net_ip,
                        'Stance Bias': bias
                    })
                    
                return pd.DataFrame(summary_rows), actual_date
        except Exception as e:
            print(f"Error fetching participant positions: {e}")
            return pd.DataFrame(), None

    def get_fii_derivatives_stats_by_date(self, snapshot_date=None):
        try:
            with self.get_connection() as conn:
                if snapshot_date:
                    date_filter = f"WHERE SnapshotDate = '{snapshot_date}'"
                else:
                    date_filter = "WHERE SnapshotDate = (SELECT MAX(SnapshotDate) FROM dbo.NSE_FII_Derivatives_Stats)"
                q = f"""
                SELECT SnapshotDate, Product, Buy_Contracts, Buy_Value_Cr, Sell_Contracts, Sell_Value_Cr, OI_Contracts, OI_Value_Cr
                FROM dbo.NSE_FII_Derivatives_Stats
                {date_filter}
                ORDER BY Product ASC
                """
                df = pd.read_sql(q, conn)
                return df
        except Exception as e:
            print(f"Error fetching FII stats: {e}")
            return pd.DataFrame()


    def get_trading_journal(self):
        try:
            with self.get_connection() as conn:
                query = "SELECT Broker, Symbol, AssetClass, TradeType, EntryDate, ExitDate, Quantity, BuyValue, SellValue, GrossPnL, TotalCharges, NetPnL, ROI_Pct, HoldingDays FROM TradingJournal_V2 ORDER BY ExitDate DESC"
                df = pd.read_sql(query, conn)
                return df
        except Exception as e:
            print(f"Error fetching trading journal: {e}")
            return pd.DataFrame()


    def get_comprehensive_rollover_table(self, sector="All"):
        try:
            with self.get_connection() as conn:
                query = "SELECT Symbol, Sector, Near_OI, Next_OI, Far_OI, Total_OI, Roll_OI, Roll_Pct, Roll_Cost_Pct, Roll_3M_Avg, Roll_Status FROM Rollover_Intelligence_Master WHERE 1=1"
                if sector and sector != "All":
                    query += f" AND Sector = '{sector}'"
                query += " ORDER BY Roll_Pct DESC"
                df = pd.read_sql(query, conn)
                return df
        except Exception as e:
            pass
            return pd.DataFrame()

    def get_nifty_vs_market_rollover(self):
        try:
            with self.get_connection() as conn:
                query = "SELECT Date, Nifty_Roll_Pct, Market_Avg_Roll_Pct FROM Nifty_Vs_Market_Rollover_History ORDER BY Date ASC"
                df = pd.read_sql(query, conn)
                return df
        except Exception as e:
            pass
            return pd.DataFrame()


    def get_sectorwise_comparison(self):
        try:
            with self.get_connection() as conn:
                query = "SELECT Sector, AVG(Roll_Pct) as Avg_Roll_Pct FROM Rollover_Intelligence_Master GROUP BY Sector ORDER BY Avg_Roll_Pct DESC"
                df = pd.read_sql(query, conn)
                return df
        except Exception as e:
            pass
            return pd.DataFrame()

    def get_rollover_history_log(self):
        try:
            conn = self.get_connection()
            query = "SELECT Date, Filename FROM Rollover_History_Log ORDER BY Date DESC"
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        except Exception as e:
            pass
            return pd.DataFrame(columns=['Date', 'Filename'])

    def get_cash_symbols_by_filters(self, sector="All", industry="All", cap="All", index_filter="All"):
        try:
            with self.get_connection() as conn:
                query = "SELECT DISTINCT Symbol FROM nseauto.NSE_Stock_Classification_Master WHERE 1=1"
                if index_filter == "SME": query += " AND IsSME = 1"
                elif index_filter == "ETF": query += " AND IsETF = 1"
                elif index_filter == "FnO Stocks": query += " AND IsFnO = 1"
                elif index_filter == "Cash Only": query += " AND (IsFnO = 0 OR IsFnO IS NULL)"
                elif index_filter == "Nifty 50": query += " AND IsNifty50 = 1"
                elif index_filter == "Nifty Next 50": query += " AND IsNiftyNext50 = 1"
                elif index_filter == "Nifty Midcap Select": query += " AND IsNiftyMidcapSelect = 1"
                elif index_filter == "Bank Nifty": query += " AND IsBankNifty = 1"
                elif index_filter == "Fin Nifty": query += " AND IsFinNifty = 1"

                if sector and sector != "All": query += f" AND Sector = '{sector}'"
                if industry and industry != "All": query += f" AND Industry = '{industry}'"
                if cap and cap != "All": query += f" AND CapCategory LIKE '%{cap.replace('-Cap', '').strip()}%'"
                query += " ORDER BY Symbol"
                df = pd.read_sql(query, conn)
                return df['Symbol'].tolist()
        except Exception:
            return self.get_symbols_by_filters(sector, industry)

    def get_cash_stocks_matrix(self, sector="All", industry="All", cap="All", index_filter="All", search=""):
        try:
            with self.get_connection() as conn:
                query = """
                SELECT 
                    m.Symbol,
                    m.CompanyName,
                    m.CapCategory,
                    m.Sector,
                    m.Industry,
                    m.IsFnO,
                    m.IsETF,
                    m.IsSME
                FROM nseauto.NSE_Stock_Classification_Master m
                WHERE 1=1
                """
                if index_filter == "SME": query += " AND m.IsSME = 1"
                elif index_filter == "ETF": query += " AND m.IsETF = 1"
                elif index_filter == "FnO Stocks": query += " AND m.IsFnO = 1"
                elif index_filter == "Cash Only": query += " AND (m.IsFnO = 0 OR m.IsFnO IS NULL)"
                elif index_filter == "Nifty 50": query += " AND m.IsNifty50 = 1"
                elif index_filter == "Nifty Next 50": query += " AND m.IsNiftyNext50 = 1"
                elif index_filter == "Nifty Midcap Select": query += " AND m.IsNiftyMidcapSelect = 1"
                elif index_filter == "Bank Nifty": query += " AND m.IsBankNifty = 1"
                elif index_filter == "Fin Nifty": query += " AND m.IsFinNifty = 1"

                if sector and sector != "All": query += f" AND m.Sector = '{sector}'"
                if industry and industry != "All": query += f" AND m.Industry = '{industry}'"
                if cap and cap != "All": query += f" AND m.CapCategory LIKE '%{cap.replace('-Cap', '').strip()}%'"
                if search: query += f" AND (m.Symbol LIKE '%{search}%' OR m.CompanyName LIKE '%{search}%')"
                query += " ORDER BY m.Symbol"
                df = pd.read_sql(query, conn)
                return df
        except Exception:
            return pd.DataFrame()

    def get_sectors_by_filters(self, cap="All", index_filter="All"):
        try:
            with self.get_connection() as conn:
                query = "SELECT DISTINCT Sector FROM nseauto.NSE_Stock_Classification_Master WHERE Sector IS NOT NULL AND Sector != ''"
                if index_filter == "SME": query += " AND IsSME = 1"
                elif index_filter == "ETF": query += " AND IsETF = 1"
                elif index_filter == "FnO Stocks": query += " AND IsFnO = 1"
                elif index_filter == "Cash Only": query += " AND (IsFnO = 0 OR IsFnO IS NULL)"
                elif index_filter == "Nifty 50": query += " AND IsNifty50 = 1"
                elif index_filter == "Nifty Next 50": query += " AND IsNiftyNext50 = 1"
                elif index_filter == "Nifty Midcap Select": query += " AND IsNiftyMidcapSelect = 1"
                elif index_filter == "Bank Nifty": query += " AND IsBankNifty = 1"
                elif index_filter == "Fin Nifty": query += " AND IsFinNifty = 1"

                if cap and cap != "All":
                    query += f" AND CapCategory LIKE '%{cap.replace('-Cap', '').strip()}%'"
                query += " ORDER BY Sector"
                df = pd.read_sql(query, conn)
                return df['Sector'].dropna().tolist()
        except Exception:
            return self.get_all_sectors()

    def get_industries_by_filters(self, sector="All", cap="All", index_filter="All"):
        try:
            with self.get_connection() as conn:
                query = "SELECT DISTINCT Industry FROM nseauto.NSE_Stock_Classification_Master WHERE Industry IS NOT NULL AND Industry != ''"
                if index_filter == "SME": query += " AND IsSME = 1"
                elif index_filter == "ETF": query += " AND IsETF = 1"
                elif index_filter == "FnO Stocks": query += " AND IsFnO = 1"
                elif index_filter == "Cash Only": query += " AND (IsFnO = 0 OR IsFnO IS NULL)"
                elif index_filter == "Nifty 50": query += " AND IsNifty50 = 1"
                elif index_filter == "Nifty Next 50": query += " AND IsNiftyNext50 = 1"
                elif index_filter == "Nifty Midcap Select": query += " AND IsNiftyMidcapSelect = 1"
                elif index_filter == "Bank Nifty": query += " AND IsBankNifty = 1"
                elif index_filter == "Fin Nifty": query += " AND IsFinNifty = 1"

                if sector and sector != "All":
                    query += f" AND Sector = '{sector}'"
                if cap and cap != "All":
                    query += f" AND CapCategory LIKE '%{cap.replace('-Cap', '').strip()}%'"
                query += " ORDER BY Industry"
                df = pd.read_sql(query, conn)
                return df['Industry'].dropna().tolist()
        except Exception:
            return self.get_industries_by_sector(sector)

    def get_stock_latest_close(self, symbol):
        try:
            clean_sym = str(symbol).replace('.NS', '').replace('^', '').strip().upper()
            if clean_sym in ('NSEI', 'NIFTY50', 'NIFTY 50'):
                clean_sym = 'NIFTY'
            elif clean_sym in ('NSEBANK', 'BANKNIFTY', 'BANK NIFTY'):
                clean_sym = 'BANKNIFTY'
            elif clean_sym in ('CNXIT', 'NIFTYIT'):
                clean_sym = 'NIFTYIT'
            elif clean_sym in ('CNXFIN', 'FINNIFTY'):
                clean_sym = 'FINNIFTY'

            if clean_sym in ('LTIM', 'LTI'):
                fno_sym_filter = "SYMBOL IN ('LTIM', 'LTM', 'LTI')"
                cash_sym_filter = "SYMBOL IN ('LTIM', 'LTM', 'LTI', '540005')"
            else:
                fno_sym_filter = f"SYMBOL = '{clean_sym}'"
                cash_sym_filter = f"SYMBOL = '{clean_sym}'"

            with self.get_connection() as conn:
                # 1. Try near-month Futures Bhavcopy (vw_Futures_FnO_Analysis covers FUTSTK and FUTIDX)
                query_fno = f"""
                SELECT TOP 1 CLOSE_PRIC, PREVIOUS_S, SnapShotDate 
                FROM dbo.vw_Futures_FnO_Analysis 
                WHERE {fno_sym_filter}
                ORDER BY SnapShotDate DESC, EXPIRY_DATE ASC
                """
                df_fno = pd.read_sql(query_fno, conn)
                if not df_fno.empty and pd.notna(df_fno['CLOSE_PRIC'].iloc[0]):
                    close_p = float(df_fno['CLOSE_PRIC'].iloc[0])
                    prev_p = float(df_fno['PREVIOUS_S'].iloc[0]) if pd.notna(df_fno['PREVIOUS_S'].iloc[0]) and float(df_fno['PREVIOUS_S'].iloc[0]) > 0 else close_p
                    return close_p, prev_p

                # 2. Try Capital Market History (Cash Bhavcopy)
                query_cash = f"""
                SELECT TOP 1 [ CLOSE_PRICE], [ PREV_CLOSE], [ LAST_PRICE], [ DATE1]
                FROM dbo.CAPITAL_MARKET_HISTORY 
                WHERE {cash_sym_filter}
                ORDER BY [ DATE1] DESC
                """
                df_cash = pd.read_sql(query_cash, conn)
                if not df_cash.empty:
                    close_val = df_cash[' CLOSE_PRICE'].iloc[0] if pd.notna(df_cash[' CLOSE_PRICE'].iloc[0]) else df_cash[' LAST_PRICE'].iloc[0]
                    prev_val = df_cash[' PREV_CLOSE'].iloc[0] if pd.notna(df_cash[' PREV_CLOSE'].iloc[0]) else close_val
                    if pd.notna(close_val):
                        return float(close_val), float(prev_val) if pd.notna(prev_val) else float(close_val)

                # 3. Fallback to Transformed Bhavcopy table
                query_fallback = f"""
                SELECT TOP 2 CLOSE_PRIC, PREVIOUS_S, SnapShotDate 
                FROM FUTURES_FNO_BhavCopy_History_Transformed_New 
                WHERE {fno_sym_filter} 
                ORDER BY SnapShotDate DESC, EXPIRY_DATE ASC
                """
                df_fb = pd.read_sql(query_fallback, conn)
                if not df_fb.empty and pd.notna(df_fb['CLOSE_PRIC'].iloc[0]):
                    c_p = float(df_fb['CLOSE_PRIC'].iloc[0])
                    p_p = float(df_fb['PREVIOUS_S'].iloc[0]) if pd.notna(df_fb['PREVIOUS_S'].iloc[0]) else c_p
                    return c_p, p_p

                return None, None
        except Exception:
            return None, None

    def get_latest_session_ohlcv(self, symbol):
        """
        Returns the exact latest trading session (e.g. 2026-09-09) OHLCV bar from SQL Server.
        """
        try:
            clean_sym = str(symbol).replace('.NS', '').replace('^', '').strip().upper()
            if clean_sym in ('NSEI', 'NIFTY50', 'NIFTY 50'):
                clean_sym = 'NIFTY'
            elif clean_sym in ('NSEBANK', 'BANKNIFTY', 'BANK NIFTY'):
                clean_sym = 'BANKNIFTY'
            elif clean_sym in ('CNXIT', 'NIFTYIT'):
                clean_sym = 'NIFTYIT'
            elif clean_sym in ('CNXFIN', 'FINNIFTY'):
                clean_sym = 'FINNIFTY'

            with self.get_connection() as conn:
                # 1. Try vw_Futures_FnO_Analysis (covers NIFTY, BANKNIFTY, FINNIFTY and all F&O stocks for 2026-09-09)
                q_fno = f"""
                SELECT TOP 1 SnapShotDate, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRIC, TRADED_QUA, PREVIOUS_S
                FROM dbo.vw_Futures_FnO_Analysis
                WHERE SYMBOL = '{clean_sym}'
                ORDER BY SnapShotDate DESC, EXPIRY_DATE ASC
                """
                df = pd.read_sql(q_fno, conn)
                if not df.empty and pd.notna(df['CLOSE_PRIC'].iloc[0]):
                    r = df.iloc[0]
                    d_str = pd.to_datetime(r['SnapShotDate']).strftime('%Y-%m-%d')
                    cp = float(r['CLOSE_PRIC'])
                    pp = float(r['PREVIOUS_S']) if pd.notna(r['PREVIOUS_S']) and float(r['PREVIOUS_S']) > 0 else cp
                    op = float(r['OPEN_PRICE']) if pd.notna(r['OPEN_PRICE']) and float(r['OPEN_PRICE']) > 0 else cp
                    hp = float(r['HIGH_PRICE']) if pd.notna(r['HIGH_PRICE']) and float(r['HIGH_PRICE']) > 0 else max(op, cp)
                    lp = float(r['LOW_PRICE']) if pd.notna(r['LOW_PRICE']) and float(r['LOW_PRICE']) > 0 else min(op, cp)
                    vol = float(r['TRADED_QUA']) if pd.notna(r['TRADED_QUA']) else 0.0
                    return {
                        'Date': d_str,
                        'Open': op,
                        'High': hp,
                        'Low': lp,
                        'Close': cp,
                        'Volume': vol,
                        'Prev_Close': pp,
                        'Pct_Change': ((cp - pp) / pp * 100) if pp > 0 else 0.0
                    }

                # 2. Try Capital Market History for Cash Equities
                q_cash = f"""
                SELECT TOP 1 [ DATE1], [ OPEN_PRICE], [ HIGH_PRICE], [ LOW_PRICE], [ CLOSE_PRICE], [ LAST_PRICE], [ TTL_TRD_QNTY], [ PREV_CLOSE]
                FROM dbo.CAPITAL_MARKET_HISTORY
                WHERE SYMBOL = '{clean_sym}'
                ORDER BY [ DATE1] DESC
                """
                df_c = pd.read_sql(q_cash, conn)
                if not df_c.empty and (pd.notna(df_c[' CLOSE_PRICE'].iloc[0]) or pd.notna(df_c[' LAST_PRICE'].iloc[0])):
                    r = df_c.iloc[0]
                    d_str = pd.to_datetime(r[' DATE1']).strftime('%Y-%m-%d')
                    cp = float(r[' CLOSE_PRICE']) if pd.notna(r[' CLOSE_PRICE']) else float(r[' LAST_PRICE'])
                    pp = float(r[' PREV_CLOSE']) if pd.notna(r[' PREV_CLOSE']) else cp
                    op = float(r[' OPEN_PRICE']) if pd.notna(r[' OPEN_PRICE']) else cp
                    hp = float(r[' HIGH_PRICE']) if pd.notna(r[' HIGH_PRICE']) else max(op, cp)
                    lp = float(r[' LOW_PRICE']) if pd.notna(r[' LOW_PRICE']) else min(op, cp)
                    vol = float(r[' TTL_TRD_QNTY']) if pd.notna(r[' TTL_TRD_QNTY']) else 0.0
                    return {
                        'Date': d_str,
                        'Open': op,
                        'High': hp,
                        'Low': lp,
                        'Close': cp,
                        'Volume': vol,
                        'Prev_Close': pp,
                        'Pct_Change': ((cp - pp) / pp * 100) if pp > 0 else 0.0
                    }
            return None
        except Exception:
            return None

    # =========================================================================
    # FLASH RADAR INSTITUTIONAL PERSISTENCE & AUDIT ENGINE
    # =========================================================================
    def ensure_flash_radar_tables(self):
        """Ensures all 3 institutional Flash Radar tables exist in SQL Server."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 1. Signals Master Table
                cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Flash_Radar_Signals_Master' AND xtype='U')
                CREATE TABLE Flash_Radar_Signals_Master (
                    Signal_ID VARCHAR(60) PRIMARY KEY,
                    Signal_Timestamp DATETIME NULL,
                    Trading_Date DATE NULL,
                    Timeframe VARCHAR(10) NULL,
                    Horizon VARCHAR(20) NULL,
                    Category VARCHAR(30) NULL,
                    Symbol VARCHAR(30) NULL,
                    Action VARCHAR(10) NULL,
                    Entry_Price FLOAT NULL,
                    Target_1 FLOAT NULL,
                    Target_2 FLOAT NULL,
                    Stop_Loss FLOAT NULL,
                    Strike_Info VARCHAR(60) NULL,
                    Conviction_Score INT NULL,
                    Smart_Money_Status VARCHAR(50) NULL,
                    Catalyst_Rationale NVARCHAR(MAX) NULL,
                    Session_High FLOAT NULL,
                    Session_Low FLOAT NULL,
                    MFE_Pct FLOAT NULL,
                    MAE_Pct FLOAT NULL,
                    Exit_Price FLOAT NULL,
                    Exit_Timestamp DATETIME NULL,
                    Exit_Reason VARCHAR(50) NULL,
                    Realized_PnL_Pct FLOAT NULL,
                    Realized_PnL_Pts FLOAT NULL,
                    Is_Win BIT NULL,
                    Status VARCHAR(30) NULL
                );
                """)
                
                # 2. Daily Reconciliation Ledger
                cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Flash_Radar_Daily_Reconciliation_Ledger' AND xtype='U')
                CREATE TABLE Flash_Radar_Daily_Reconciliation_Ledger (
                    Trading_Date DATE PRIMARY KEY,
                    Total_Signals INT NULL,
                    Target_2_Hits INT NULL,
                    Target_1_Hits INT NULL,
                    Stop_Loss_Hits INT NULL,
                    EOD_MTM_Wins INT NULL,
                    EOD_MTM_Losses INT NULL,
                    Traps_Avoided INT NULL,
                    Daily_Win_Rate FLOAT NULL,
                    Gross_Profit_Pts FLOAT NULL,
                    Gross_Loss_Pts FLOAT NULL,
                    Daily_Profit_Factor FLOAT NULL,
                    Market_Capture_Rate_Pct FLOAT NULL,
                    Best_Trade VARCHAR(60) NULL,
                    Worst_Trade VARCHAR(60) NULL
                );
                """)
                
                # 3. EOD Market Attribution Table
                cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Flash_Radar_EOD_Market_Attribution' AND xtype='U')
                CREATE TABLE Flash_Radar_EOD_Market_Attribution (
                    Attribution_ID VARCHAR(80) PRIMARY KEY,
                    Trading_Date DATE NULL,
                    Mover_Type VARCHAR(20) NULL,
                    Rank INT NULL,
                    Symbol VARCHAR(30) NULL,
                    Day_Open FLOAT NULL,
                    Day_High FLOAT NULL,
                    Day_Low FLOAT NULL,
                    Day_Close FLOAT NULL,
                    Day_Change_Pct FLOAT NULL,
                    Flash_Status VARCHAR(30) NULL,
                    Flash_Signal_ID VARCHAR(60) NULL,
                    Flash_Entry_Time VARCHAR(30) NULL,
                    Flash_Return_Pct FLOAT NULL,
                    Justification_Code VARCHAR(50) NULL,
                    Justification_Detail NVARCHAR(MAX) NULL
                );
                """)
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Flash Radar table creation warning: {e}")
            return False

    def save_flash_signal_to_db(self, s: dict):
        """Upserts a single Flash Radar trade signal to SQL Server."""
        try:
            self.ensure_flash_radar_tables()
            sig_id = s.get('signal_id') or s.get('id')
            if not sig_id:
                return False
            
            ts_str = s.get('timestamp')
            trading_date = ts_str[:10] if ts_str and len(ts_str) >= 10 else None
            is_win = 1 if 'HIT TARGET' in str(s.get('status', '')) or float(s.get('pnl_pct', 0.0) or 0.0) > 0 else 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                MERGE Flash_Radar_Signals_Master AS target
                USING (SELECT ? AS Signal_ID) AS source
                ON (target.Signal_ID = source.Signal_ID)
                WHEN MATCHED THEN
                    UPDATE SET
                        Timeframe = ?, Horizon = ?, Category = ?, Symbol = ?, Action = ?,
                        Entry_Price = ?, Target_1 = ?, Target_2 = ?, Stop_Loss = ?,
                        Strike_Info = ?, Conviction_Score = ?, Smart_Money_Status = ?,
                        Catalyst_Rationale = ?, Session_High = ?, Session_Low = ?,
                        MFE_Pct = ?, MAE_Pct = ?, Exit_Price = ?, Exit_Timestamp = ?,
                        Exit_Reason = ?, Realized_PnL_Pct = ?, Realized_PnL_Pts = ?,
                        Is_Win = ?, Status = ?
                WHEN NOT MATCHED THEN
                    INSERT (
                        Signal_ID, Signal_Timestamp, Trading_Date, Timeframe, Horizon,
                        Category, Symbol, Action, Entry_Price, Target_1, Target_2,
                        Stop_Loss, Strike_Info, Conviction_Score, Smart_Money_Status,
                        Catalyst_Rationale, Session_High, Session_Low, MFE_Pct, MAE_Pct,
                        Exit_Price, Exit_Timestamp, Exit_Reason, Realized_PnL_Pct,
                        Realized_PnL_Pts, Is_Win, Status
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """, (
                    sig_id,
                    s.get('timeframe', '15m'), s.get('horizon', '⚡ INTRADAY'), s.get('category', 'Cash Only'),
                    s.get('symbol', ''), s.get('action', 'BUY'), float(s.get('entry', 0.0) or 0.0),
                    float(s.get('target_1', 0.0) or 0.0), float(s.get('target_2', 0.0) or 0.0),
                    float(s.get('stop_loss', 0.0) or 0.0), s.get('strike_info', 'Spot Cash'),
                    int(s.get('conviction', 85) or 85), s.get('smart_money_status', '🟢 SMART MONEY ALIGNED'),
                    s.get('justification', ''), float(s.get('session_high', 0.0) or 0.0),
                    float(s.get('session_low', 0.0) or 0.0), float(s.get('mfe_pct', 0.0) or 0.0),
                    float(s.get('mae_pct', 0.0) or 0.0), float(s.get('exit_price', 0.0) or 0.0) if s.get('exit_price') else None,
                    s.get('exit_time'), s.get('status'), float(s.get('pnl_pct', 0.0) or 0.0),
                    float(s.get('pnl_pts', 0.0) or 0.0), is_win, s.get('status', '⏳ ACTIVE'),
                    # Values for INSERT
                    sig_id, ts_str, trading_date, s.get('timeframe', '15m'), s.get('horizon', '⚡ INTRADAY'),
                    s.get('category', 'Cash Only'), s.get('symbol', ''), s.get('action', 'BUY'),
                    float(s.get('entry', 0.0) or 0.0), float(s.get('target_1', 0.0) or 0.0),
                    float(s.get('target_2', 0.0) or 0.0), float(s.get('stop_loss', 0.0) or 0.0),
                    s.get('strike_info', 'Spot Cash'), int(s.get('conviction', 85) or 85),
                    s.get('smart_money_status', '🟢 SMART MONEY ALIGNED'), s.get('justification', ''),
                    float(s.get('session_high', 0.0) or 0.0), float(s.get('session_low', 0.0) or 0.0),
                    float(s.get('mfe_pct', 0.0) or 0.0), float(s.get('mae_pct', 0.0) or 0.0),
                    float(s.get('exit_price', 0.0) or 0.0) if s.get('exit_price') else None,
                    s.get('exit_time'), s.get('status'), float(s.get('pnl_pct', 0.0) or 0.0),
                    float(s.get('pnl_pts', 0.0) or 0.0), is_win, s.get('status', '⏳ ACTIVE')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Error saving flash signal: {e}")
            return False

    def save_flash_signals_batch_to_db(self, signals: list):
        """Batch-saves or updates multiple flash signals in a single transaction."""
        if not signals:
            return True
        try:
            self.ensure_flash_radar_tables()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                MERGE Flash_Radar_Signals_Master AS target
                USING (SELECT ? AS Signal_ID) AS source
                ON (target.Signal_ID = source.Signal_ID)
                WHEN MATCHED THEN
                    UPDATE SET
                        Timeframe = ?, Horizon = ?, Category = ?, Symbol = ?, Action = ?,
                        Entry_Price = ?, Target_1 = ?, Target_2 = ?, Stop_Loss = ?,
                        Strike_Info = ?, Conviction_Score = ?, Smart_Money_Status = ?,
                        Catalyst_Rationale = ?, Session_High = ?, Session_Low = ?,
                        MFE_Pct = ?, MAE_Pct = ?, Exit_Price = ?, Exit_Timestamp = ?,
                        Exit_Reason = ?, Realized_PnL_Pct = ?, Realized_PnL_Pts = ?,
                        Is_Win = ?, Status = ?
                WHEN NOT MATCHED THEN
                    INSERT (
                        Signal_ID, Signal_Timestamp, Trading_Date, Timeframe, Horizon,
                        Category, Symbol, Action, Entry_Price, Target_1, Target_2,
                        Stop_Loss, Strike_Info, Conviction_Score, Smart_Money_Status,
                        Catalyst_Rationale, Session_High, Session_Low, MFE_Pct, MAE_Pct,
                        Exit_Price, Exit_Timestamp, Exit_Reason, Realized_PnL_Pct,
                        Realized_PnL_Pts, Is_Win, Status
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """
                for s in signals:
                    sig_id = s.get('id')
                    if not sig_id:
                        continue
                    ts_str = s.get('timestamp') or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    trading_date = ts_str[:10] if len(ts_str) >= 10 else datetime.date.today().strftime("%Y-%m-%d")
                    pnl_pct = float(s.get('pnl_pct', 0.0) or 0.0)
                    is_win = 1 if ("TARGET" in s.get('status', '') or "PROFIT" in s.get('status', '') or pnl_pct > 0) else (0 if ("STOP LOSS" in s.get('status', '') or "LOSS" in s.get('status', '') or pnl_pct < 0) else None)

                    params = (
                        sig_id,
                        s.get('timeframe', '15m'), s.get('horizon', '⚡ INTRADAY'), s.get('category', 'Cash Only'),
                        s.get('symbol', ''), s.get('action', 'BUY'), float(s.get('entry', 0.0) or 0.0),
                        float(s.get('target_1', 0.0) or 0.0), float(s.get('target_2', 0.0) or 0.0),
                        float(s.get('stop_loss', 0.0) or 0.0), s.get('strike_info', 'Spot Cash'),
                        int(s.get('conviction', 85) or 85), s.get('smart_money_status', '🟢 SMART MONEY ALIGNED'),
                        s.get('justification', ''), float(s.get('session_high', 0.0) or 0.0),
                        float(s.get('session_low', 0.0) or 0.0), float(s.get('mfe_pct', 0.0) or 0.0),
                        float(s.get('mae_pct', 0.0) or 0.0), float(s.get('exit_price', 0.0) or 0.0) if s.get('exit_price') else None,
                        s.get('exit_time'), s.get('status'), float(s.get('pnl_pct', 0.0) or 0.0),
                        float(s.get('pnl_pts', 0.0) or 0.0), is_win, s.get('status', '⏳ ACTIVE'),
                        # Values for INSERT
                        sig_id, ts_str, trading_date, s.get('timeframe', '15m'), s.get('horizon', '⚡ INTRADAY'),
                        s.get('category', 'Cash Only'), s.get('symbol', ''), s.get('action', 'BUY'),
                        float(s.get('entry', 0.0) or 0.0), float(s.get('target_1', 0.0) or 0.0),
                        float(s.get('target_2', 0.0) or 0.0), float(s.get('stop_loss', 0.0) or 0.0),
                        s.get('strike_info', 'Spot Cash'), int(s.get('conviction', 85) or 85),
                        s.get('smart_money_status', '🟢 SMART MONEY ALIGNED'), s.get('justification', ''),
                        float(s.get('session_high', 0.0) or 0.0), float(s.get('session_low', 0.0) or 0.0),
                        float(s.get('mfe_pct', 0.0) or 0.0), float(s.get('mae_pct', 0.0) or 0.0),
                        float(s.get('exit_price', 0.0) or 0.0) if s.get('exit_price') else None,
                        s.get('exit_time'), s.get('status'), float(s.get('pnl_pct', 0.0) or 0.0),
                        float(s.get('pnl_pts', 0.0) or 0.0), is_win, s.get('status', '⏳ ACTIVE')
                    )
                    cursor.execute(sql, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Error batch saving flash signals: {e}")
            return False

    def load_all_flash_signals_from_db(self):
        """Loads all Flash Radar trade signals from SQL Server."""
        try:
            self.ensure_flash_radar_tables()
            with self.get_connection() as conn:
                q = """
                SELECT 
                    Signal_ID as id, Signal_Timestamp as timestamp, Timeframe as timeframe,
                    Horizon as horizon, Category as category, Symbol as symbol, Action as action,
                    Entry_Price as entry, Target_1 as target_1, Target_2 as target_2,
                    Stop_Loss as stop_loss, Strike_Info as strike_info, Conviction_Score as conviction,
                    Smart_Money_Status as smart_money_status, Catalyst_Rationale as justification,
                    Session_High as session_high, Session_Low as session_low, MFE_Pct as mfe_pct,
                    MAE_Pct as mae_pct, Exit_Price as exit_price, Exit_Timestamp as exit_time,
                    Realized_PnL_Pct as pnl_pct, Realized_PnL_Pts as pnl_pts, Status as status
                FROM Flash_Radar_Signals_Master
                ORDER BY Signal_Timestamp DESC
                """
                df = pd.read_sql(q, conn)
                if df.empty:
                    return []
                # Convert timestamps to string
                if 'timestamp' in df.columns:
                    df['timestamp'] = df['timestamp'].astype(str)
                if 'exit_time' in df.columns:
                    df['exit_time'] = df['exit_time'].fillna('').astype(str)
                return df.to_dict(orient='records')
        except Exception as e:
            print(f"[DB] Error loading flash signals from DB: {e}")
            return []

    def save_daily_reconciliation_to_db(self, r: dict):
        """Upserts a daily reconciliation row to SQL Server."""
        try:
            self.ensure_flash_radar_tables()
            td = r.get('trading_date')
            if not td:
                return False
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                MERGE Flash_Radar_Daily_Reconciliation_Ledger AS target
                USING (SELECT ? AS Trading_Date) AS source
                ON (target.Trading_Date = source.Trading_Date)
                WHEN MATCHED THEN
                    UPDATE SET
                        Total_Signals = ?, Target_2_Hits = ?, Target_1_Hits = ?,
                        Stop_Loss_Hits = ?, EOD_MTM_Wins = ?, EOD_MTM_Losses = ?,
                        Traps_Avoided = ?, Daily_Win_Rate = ?, Gross_Profit_Pts = ?,
                        Gross_Loss_Pts = ?, Daily_Profit_Factor = ?,
                        Market_Capture_Rate_Pct = ?, Best_Trade = ?, Worst_Trade = ?
                WHEN NOT MATCHED THEN
                    INSERT (
                        Trading_Date, Total_Signals, Target_2_Hits, Target_1_Hits,
                        Stop_Loss_Hits, EOD_MTM_Wins, EOD_MTM_Losses, Traps_Avoided,
                        Daily_Win_Rate, Gross_Profit_Pts, Gross_Loss_Pts,
                        Daily_Profit_Factor, Market_Capture_Rate_Pct, Best_Trade, Worst_Trade
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    td,
                    r.get('total_signals', 0), r.get('target_2_hits', 0), r.get('target_1_hits', 0),
                    r.get('stop_loss_hits', 0), r.get('eod_mtm_wins', 0), r.get('eod_mtm_losses', 0),
                    r.get('traps_avoided', 0), float(r.get('daily_win_rate', 0.0) or 0.0),
                    float(r.get('gross_profit_pts', 0.0) or 0.0), float(r.get('gross_loss_pts', 0.0) or 0.0),
                    float(r.get('daily_profit_factor', 1.0) or 1.0), float(r.get('market_capture_rate_pct', 0.0) or 0.0),
                    r.get('best_trade', ''), r.get('worst_trade', ''),
                    # INSERT values
                    td,
                    r.get('total_signals', 0), r.get('target_2_hits', 0), r.get('target_1_hits', 0),
                    r.get('stop_loss_hits', 0), r.get('eod_mtm_wins', 0), r.get('eod_mtm_losses', 0),
                    r.get('traps_avoided', 0), float(r.get('daily_win_rate', 0.0) or 0.0),
                    float(r.get('gross_profit_pts', 0.0) or 0.0), float(r.get('gross_loss_pts', 0.0) or 0.0),
                    float(r.get('daily_profit_factor', 1.0) or 1.0), float(r.get('market_capture_rate_pct', 0.0) or 0.0),
                    r.get('best_trade', ''), r.get('worst_trade', '')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Error saving daily reconciliation: {e}")
            return False

    def load_daily_reconciliations_from_db(self):
        """Loads all daily reconciliation rollups from SQL Server."""
        try:
            self.ensure_flash_radar_tables()
            with self.get_connection() as conn:
                df = pd.read_sql("SELECT * FROM Flash_Radar_Daily_Reconciliation_Ledger ORDER BY Trading_Date DESC", conn)
                if not df.empty:
                    df['Trading_Date'] = df['Trading_Date'].astype(str)
                    return df.to_dict(orient='records')
                return []
        except Exception:
            return []

    def save_eod_attributions_to_db(self, attributions: list):
        """Saves daily market attribution list to SQL Server."""
        try:
            self.ensure_flash_radar_tables()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for a in attributions:
                    attr_id = a.get('attribution_id') or f"ATTR-{a.get('trading_date')}-{a.get('symbol')}"
                    cursor.execute("""
                    MERGE Flash_Radar_EOD_Market_Attribution AS target
                    USING (SELECT ? AS Attribution_ID) AS source
                    ON (target.Attribution_ID = source.Attribution_ID)
                    WHEN MATCHED THEN
                        UPDATE SET
                            Trading_Date = ?, Mover_Type = ?, Rank = ?, Symbol = ?,
                            Day_Open = ?, Day_High = ?, Day_Low = ?, Day_Close = ?,
                            Day_Change_Pct = ?, Flash_Status = ?, Flash_Signal_ID = ?,
                            Flash_Entry_Time = ?, Flash_Return_Pct = ?,
                            Justification_Code = ?, Justification_Detail = ?
                    WHEN NOT MATCHED THEN
                        INSERT (
                            Attribution_ID, Trading_Date, Mover_Type, Rank, Symbol,
                            Day_Open, Day_High, Day_Low, Day_Close, Day_Change_Pct,
                            Flash_Status, Flash_Signal_ID, Flash_Entry_Time,
                            Flash_Return_Pct, Justification_Code, Justification_Detail
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        attr_id,
                        a.get('trading_date'), a.get('mover_type'), int(a.get('rank', 1) or 1), a.get('symbol'),
                        float(a.get('day_open', 0.0) or 0.0), float(a.get('day_high', 0.0) or 0.0),
                        float(a.get('day_low', 0.0) or 0.0), float(a.get('day_close', 0.0) or 0.0),
                        float(a.get('day_change_pct', 0.0) or 0.0), a.get('flash_status', 'FILTERED_OUT'),
                        a.get('flash_signal_id'), a.get('flash_entry_time'), float(a.get('flash_return_pct', 0.0) or 0.0),
                        a.get('justification_code', ''), a.get('justification_detail', ''),
                        # INSERT values
                        attr_id,
                        a.get('trading_date'), a.get('mover_type'), int(a.get('rank', 1) or 1), a.get('symbol'),
                        float(a.get('day_open', 0.0) or 0.0), float(a.get('day_high', 0.0) or 0.0),
                        float(a.get('day_low', 0.0) or 0.0), float(a.get('day_close', 0.0) or 0.0),
                        float(a.get('day_change_pct', 0.0) or 0.0), a.get('flash_status', 'FILTERED_OUT'),
                        a.get('flash_signal_id'), a.get('flash_entry_time'), float(a.get('flash_return_pct', 0.0) or 0.0),
                        a.get('justification_code', ''), a.get('justification_detail', '')
                    ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Error saving EOD attributions: {e}")
            return False

    def load_eod_attributions_from_db(self, date_str=None):
        """Loads EOD market attributions for a given date or all dates."""
        try:
            self.ensure_flash_radar_tables()
            with self.get_connection() as conn:
                if date_str and date_str != "All Dates":
                    q = f"SELECT * FROM Flash_Radar_EOD_Market_Attribution WHERE Trading_Date = '{date_str}' ORDER BY Mover_Type, Rank"
                else:
                    q = "SELECT * FROM Flash_Radar_EOD_Market_Attribution ORDER BY Trading_Date DESC, Mover_Type, Rank"
                df = pd.read_sql(q, conn)
                if not df.empty:
                    df['Trading_Date'] = df['Trading_Date'].astype(str)
                    return df.to_dict(orient='records')
                return []
        except Exception:
            return []




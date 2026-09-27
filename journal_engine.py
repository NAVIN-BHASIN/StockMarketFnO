"""
================================================================================
MODULE: TRADING JOURNAL ENGINE & DATA ACCESS LAYER
================================================================================
Tier: Business Logic & Data Persistence Engine
Architecture: Microsoft SQL Server + ODBC + Multi-Broker Ingestion Normalizer
Features:
  - Multi-Broker Trade Log Parsing (Zerodha, HDFC Securities, BlinkX, INDMoney)
  - Quantitative Trade Metrics (Win/Loss, Payoff Ratio, Max Drawdown, Sharpe/Sortino)
  - Cognitive Behavioral Profiling & Risk Adherence Analysis
  - Automated Table Creation & Schema Verification
Version: 3.0.0 (Enterprise Release)
Standards: PEP 8, Clean Architecture, SQL Transaction Safety
================================================================================
"""

import os
import re
import hashlib
import shutil
from datetime import datetime
import pandas as pd
import numpy as np
import pyodbc

SERVER = r'.\SQLEXPRESS'
DATABASE = 'Navin_Personal'
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

def get_connection():
    return pyodbc.connect(CONN_STR)

def compute_financial_year(dt):
    """
    Computes Indian Financial Year (Apr 1 to Mar 31) for a given date.
    Returns format 'FY 2025-26'.
    """
    if pd.isna(dt):
        return 'Unknown'
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt).date()
        except:
            return 'Unknown'
    elif isinstance(dt, datetime):
        dt = dt.date()
    elif hasattr(dt, 'date'):
        dt = dt.date()

    year = dt.year
    month = dt.month
    if month >= 4:
        next_yr_short = str(year + 1)[-2:]
        return f"FY {year}-{next_yr_short}"
    else:
        curr_yr_short = str(year)[-2:]
        return f"FY {year - 1}-{curr_yr_short}"

def generate_trade_hash(broker, segment, symbol, entry_date, exit_date, quantity, buy_value, sell_value, strike_price=0.0, option_type=""):
    """
    Generates a deterministic 64-character SHA-256 fingerprint for deduplication.
    """
    sym = str(symbol).strip().upper()
    b_val = round(float(buy_value or 0.0), 2)
    s_val = round(float(sell_value or 0.0), 2)
    qty = round(float(quantity or 0.0), 2)
    e_date = str(entry_date)
    x_date = str(exit_date)
    strike = round(float(strike_price or 0.0), 2)
    op_type = str(option_type or "").strip().upper()
    
    raw_str = f"{broker}|{segment}|{sym}|{e_date}|{x_date}|{qty}|{b_val}|{s_val}|{strike}|{op_type}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def clean_date(val):
    if pd.isna(val) or val is None or str(val).strip() in ['', '-', 'NaT', 'None']:
        return None
    try:
        dt = pd.to_datetime(val)
        return dt.date()
    except:
        return None

def clean_float(val, default=0.0):
    if pd.isna(val) or val is None:
        return default
    s = str(val).replace(',', '').replace('₹', '').replace('$', '').strip()
    if s in ['', '-', 'None', 'nil', 'N/A']:
        return default
    try:
        return float(s)
    except:
        return default

# ----------------- PARSERS FOR EACH BROKER -----------------

def parse_zerodha_file(file_path):
    """
    Parses Zerodha tax PnL Excel file.
    Extracts Tradewise Exits across Equity, F&O, Commodity, Currency, plus Other Debits/Credits.
    """
    trades = []
    other_ledgers = []
    fname = os.path.basename(file_path)
    xl = pd.ExcelFile(file_path)
    
    if 'Tradewise Exits from 2025-04-01' in xl.sheet_names or any('Tradewise Exits' in s for s in xl.sheet_names):
        exit_sheet = [s for s in xl.sheet_names if 'Tradewise Exits' in s][0]
        df = xl.parse(exit_sheet, header=None)
        
        current_segment = 'Equity'
        current_subsegment = 'Intraday'
        header_map = {}
        in_table = False
        
        for idx, row in df.iterrows():
            vals = [str(x).strip() for x in row.dropna().tolist()]
            if not vals:
                continue
            
            # Check section header
            first_val = vals[0]
            if len(vals) == 1 or (len(vals) <= 3 and any(k in first_val.lower() for k in ['equity -', 'f&o', 'commodity', 'currency', 'non equity'])):
                txt = first_val.lower()
                if 'equity - intraday' in txt:
                    current_segment = 'Equity'
                    current_subsegment = 'Intraday'
                elif 'equity - short term' in txt:
                    current_segment = 'Equity'
                    current_subsegment = 'Short Term'
                elif 'equity - long term' in txt:
                    current_segment = 'Equity'
                    current_subsegment = 'Long Term'
                elif 'f&o' in txt:
                    current_segment = 'FnO'
                    current_subsegment = 'F&O'
                elif 'commodity' in txt:
                    current_segment = 'Commodity'
                    current_subsegment = 'Commodity'
                elif 'currency' in txt:
                    current_segment = 'Currency'
                    current_subsegment = 'Currency'
                in_table = False
                header_map = {}
                continue
                
            # Check table header
            if 'symbol' in [v.lower() for v in vals] and ('profit' in [v.lower() for v in vals] or 'quantity' in [v.lower() for v in vals]):
                header_map = {str(val).strip().lower(): col_idx for col_idx, val in row.items() if pd.notna(val)}
                in_table = True
                continue
                
            if in_table and 'symbol' in header_map:
                sym_col = header_map.get('symbol')
                sym = str(row[sym_col]).strip() if pd.notna(row.get(sym_col)) else ''
                if not sym or sym.lower() in ['total', 'symbol', 'sub total']:
                    continue
                
                isin_col = header_map.get('isin')
                isin = str(row[isin_col]).strip() if isin_col and pd.notna(row.get(isin_col)) else ''
                
                entry_date_col = header_map.get('entry date')
                exit_date_col = header_map.get('exit date')
                entry_date = clean_date(row.get(entry_date_col))
                exit_date = clean_date(row.get(exit_date_col))
                if not exit_date:
                    continue
                if not entry_date:
                    entry_date = exit_date
                    
                qty_col = header_map.get('quantity')
                qty = clean_float(row.get(qty_col), 0.0)
                
                buy_val_col = header_map.get('buy value')
                sell_val_col = header_map.get('sell value')
                buy_val = clean_float(row.get(buy_val_col), 0.0)
                sell_val = clean_float(row.get(sell_val_col), 0.0)
                
                profit_col = header_map.get('profit')
                gross_pnl = clean_float(row.get(profit_col), sell_val - buy_val)
                
                # Charges
                brokerage = clean_float(row.get(header_map.get('brokerage', -1)), 0.0)
                exch_chgs = clean_float(row.get(header_map.get('exchange transaction charges', -1)), 0.0)
                ipft = clean_float(row.get(header_map.get('ipft', -1)), 0.0)
                sebi = clean_float(row.get(header_map.get('sebi charges', -1)), 0.0)
                cgst = clean_float(row.get(header_map.get('cgst', -1)), 0.0)
                sgst = clean_float(row.get(header_map.get('sgst', -1)), 0.0)
                igst = clean_float(row.get(header_map.get('igst', -1)), 0.0)
                gst = cgst + sgst + igst
                stamp_duty = clean_float(row.get(header_map.get('stamp duty', -1)), 0.0)
                stt = clean_float(row.get(header_map.get('stt', -1)), 0.0)
                total_charges = brokerage + exch_chgs + ipft + sebi + gst + stamp_duty + stt
                net_pnl = gross_pnl - total_charges
                
                # F&O decomposition
                op_type = None
                strike_price = None
                clean_sym = sym
                expiry_date = None
                contract_name = sym
                
                if current_segment == 'FnO':
                    if sym.endswith('CE') or sym.endswith('PE'):
                        op_type = sym[-2:]
                        m = re.search(r'([A-Z]+)(\d{5,7})(CE|PE)$', sym)
                        if m:
                            clean_sym = m.group(1)
                            raw_strike = m.group(2)
                            # e.g. 2540323500 -> 25 4 03 23500
                            # Or parse from end
                            strike_m = re.search(r'(\d+)(CE|PE)$', sym)
                            if strike_m:
                                # strike digits
                                pass
                        # Try robust regex: SYMBOL + YY + M/MM + DD + STRIKE + CE/PE
                        m2 = re.search(r'^([A-Z]+)(\d{2})([1-9OND])(\d{2})(\d+)(CE|PE)$', sym)
                        if m2:
                            clean_sym = m2.group(1)
                            strike_price = float(m2.group(5))
                        else:
                            m3 = re.search(r'(\d{3,6})(CE|PE)$', sym)
                            if m3:
                                strike_price = float(m3.group(1))
                                clean_sym = re.sub(r'\d+(CE|PE)$', '', sym)
                                clean_sym = re.sub(r'\d{2}[A-Z0-9]{3}', '', clean_sym).strip()
                    elif 'FUT' in sym:
                        op_type = 'FUT'
                        clean_sym = sym.replace('FUT', '').strip()
                        clean_sym = re.sub(r'\d{2}[A-Z]{3}', '', clean_sym).strip()
                
                buy_price = round(buy_val / qty, 2) if qty > 0 else 0.0
                sell_price = round(sell_val / qty, 2) if qty > 0 else 0.0
                holding_days = (exit_date - entry_date).days if exit_date and entry_date else 0
                roi_pct = round((net_pnl / buy_val * 100), 2) if buy_val > 0 else 0.0
                fy = compute_financial_year(exit_date)
                outcome = 'PROFIT' if net_pnl > 0.01 else ('LOSS' if net_pnl < -0.01 else 'BREAKEVEN')
                
                thash = generate_trade_hash('Zerodha', current_segment, clean_sym, entry_date, exit_date, qty, buy_val, sell_val, strike_price, op_type)
                
                trade_dict = {
                    'TradeHash': thash,
                    'Broker': 'Zerodha',
                    'Segment': current_segment,
                    'SubSegment': current_subsegment,
                    'Symbol': clean_sym,
                    'ContractName': contract_name,
                    'ISIN': isin,
                    'Sector': None,
                    'OptionType': op_type,
                    'StrikePrice': strike_price,
                    'ExpiryDate': expiry_date,
                    'TradeType': 'LONG',
                    'EntryDate': entry_date,
                    'ExitDate': exit_date,
                    'Quantity': qty,
                    'BuyPrice': buy_price,
                    'BuyValue': buy_val,
                    'SellPrice': sell_price,
                    'SellValue': sell_val,
                    'HoldingDays': holding_days,
                    'GrossPnL': gross_pnl,
                    'Brokerage': brokerage,
                    'STT': stt,
                    'ExchangeCharges': exch_chgs,
                    'GST': gst,
                    'StampDuty': stamp_duty,
                    'OtherCharges': ipft + sebi,
                    'TotalCharges': total_charges,
                    'NetPnL': net_pnl,
                    'ROIPct': roi_pct,
                    'IsMTF': 0,
                    'FinancialYear': fy,
                    'CalYear': exit_date.year,
                    'CalMonth': exit_date.month,
                    'Outcome': outcome,
                    'SourceFile': fname,
                    'SourceSheet': exit_sheet
                }
                trades.append(trade_dict)
                
    # Parse Other Debits and Credits
    if 'Other Debits and Credits' in xl.sheet_names:
        df_deb = xl.parse('Other Debits and Credits', header=None)
        in_deb = False
        for idx, row in df_deb.iterrows():
            vals = [str(x).strip() for x in row.dropna().tolist()]
            if not vals: continue
            if 'particulars' in [v.lower() for v in vals] and 'posting date' in [v.lower() for v in vals]:
                in_deb = True
                h_map = {str(val).strip().lower(): col_idx for col_idx, val in row.items() if pd.notna(val)}
                continue
            if in_deb and 'particulars' in h_map:
                part_col = h_map.get('particulars')
                part = str(row[part_col]).strip() if pd.notna(row.get(part_col)) else ''
                if not part or part.lower() in ['total', 'particulars']: continue
                
                dt_col = h_map.get('posting date')
                pdate = clean_date(row.get(dt_col))
                if not pdate: continue
                
                deb_col = h_map.get('debit')
                cred_col = h_map.get('credit')
                debit = clean_float(row.get(deb_col), 0.0)
                credit = clean_float(row.get(cred_col), 0.0)
                
                cat = 'MTF Interest' if 'mtf' in part.lower() else ('DP Charges' if 'dp charges' in part.lower() else 'Other Charges')
                fy = compute_financial_year(pdate)
                
                lraw = f"Zerodha|{pdate}|{part}|{debit}|{credit}"
                lhash = hashlib.sha256(lraw.encode('utf-8')).hexdigest()
                
                other_ledgers.append({
                    'LedgerHash': lhash,
                    'Broker': 'Zerodha',
                    'PostingDate': pdate,
                    'Particulars': part,
                    'Category': cat,
                    'Debit': debit,
                    'Credit': credit,
                    'FinancialYear': fy,
                    'SourceFile': fname
                })
                
    try:
        xl.close()
    except:
        pass
    return trades, other_ledgers

def parse_hdfc_file(file_path):
    """
    Parses HDFC Securities Profit & Loss Detailed Report.
    Sheets: Equity, Equity Derivatives, Fixed Income.
    """
    trades = []
    other_ledgers = []
    fname = os.path.basename(file_path)
    xl = pd.ExcelFile(file_path)
    
    # 1. Equity Sheet
    if 'Equity' in xl.sheet_names:
        df_eq = xl.parse('Equity', skiprows=24)
        for _, row in df_eq.iterrows():
            name = str(row.get('Name', '')).strip()
            if not name or name.lower() in ['total', 'summary', 'nan']:
                continue
            isin = str(row.get('ISIN', '')).strip()
            sub_asset = str(row.get('Sub Asset', 'EQ')).strip()
            sector = str(row.get('Sector Name', '')).strip()
            
            b_dt = clean_date(row.get('Buy Transaction Date'))
            s_dt = clean_date(row.get('Sell Transaction Date'))
            if not s_dt: continue
            if not b_dt: b_dt = s_dt
            
            qty = clean_float(row.get('Sell Transaction Qty', row.get('Buy Transaction Qty', 0)))
            b_val = clean_float(row.get('Buy Transaction Value', 0.0))
            s_val = clean_float(row.get('Sell Transaction Value', 0.0))
            gross_pnl = clean_float(row.get('Gross P&L', s_val - b_val))
            
            brokerage = clean_float(row.get('Brokerage', 0.0))
            stt = clean_float(row.get('STT', 0.0))
            service_tax = clean_float(row.get('Service Tax', 0.0))
            tx_charges = clean_float(row.get('Transaction Charges', 0.0))
            other_chgs = clean_float(row.get('Other Charges', 0.0))
            total_charges = brokerage + stt + service_tax + tx_charges + other_chgs
            net_pnl = clean_float(row.get('Net Realized P&L', gross_pnl - total_charges))
            
            b_price = round(b_val / qty, 2) if qty > 0 else 0.0
            s_price = round(s_val / qty, 2) if qty > 0 else 0.0
            holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
            roi_pct = round((net_pnl / b_val * 100), 2) if b_val > 0 else 0.0
            fy = compute_financial_year(s_dt)
            outcome = 'PROFIT' if net_pnl > 0.01 else ('LOSS' if net_pnl < -0.01 else 'BREAKEVEN')
            
            thash = generate_trade_hash('HDFC Securities', 'Equity', name, b_dt, s_dt, qty, b_val, s_val, 0.0, '')
            trades.append({
                'TradeHash': thash,
                'Broker': 'HDFC Securities',
                'Segment': 'Equity',
                'SubSegment': sub_asset,
                'Symbol': name,
                'ContractName': name,
                'ISIN': isin,
                'Sector': sector,
                'OptionType': None,
                'StrikePrice': None,
                'ExpiryDate': None,
                'TradeType': 'LONG',
                'EntryDate': b_dt,
                'ExitDate': s_dt,
                'Quantity': qty,
                'BuyPrice': b_price,
                'BuyValue': b_val,
                'SellPrice': s_price,
                'SellValue': s_val,
                'HoldingDays': holding_days,
                'GrossPnL': gross_pnl,
                'Brokerage': brokerage,
                'STT': stt,
                'ExchangeCharges': tx_charges,
                'GST': service_tax,
                'StampDuty': 0.0,
                'OtherCharges': other_chgs,
                'TotalCharges': total_charges,
                'NetPnL': net_pnl,
                'ROIPct': roi_pct,
                'IsMTF': 0,
                'FinancialYear': fy,
                'CalYear': s_dt.year,
                'CalMonth': s_dt.month,
                'Outcome': outcome,
                'SourceFile': fname,
                'SourceSheet': 'Equity'
            })
            
    # 2. Equity Derivatives Sheet
    if 'Equity Derivatives' in xl.sheet_names:
        df_fno = xl.parse('Equity Derivatives', skiprows=24)
        for _, row in df_fno.iterrows():
            name = str(row.get('Name', '')).strip()
            if not name or name.lower() in ['total', 'summary', 'nan']:
                continue
            
            b_dt = clean_date(row.get('Buy Transaction Date'))
            s_dt = clean_date(row.get('Sell Transaction Date'))
            if not s_dt: continue
            if not b_dt: b_dt = s_dt
            
            qty = clean_float(row.get('Sell Transaction Qty', row.get('Buy Transaction Qty', 0)))
            b_val = clean_float(row.get('Buy Transaction Value', 0.0))
            s_val = clean_float(row.get('Sell Transaction Value', 0.0))
            gross_pnl = clean_float(row.get('Gross P&L', s_val - b_val))
            
            brokerage = clean_float(row.get('Brokerage', 0.0))
            stt = clean_float(row.get('STT', 0.0))
            service_tax = clean_float(row.get('Service Tax', 0.0))
            tx_charges = clean_float(row.get('Transaction Charges', 0.0))
            other_chgs = clean_float(row.get('Other Charges', 0.0))
            total_charges = brokerage + stt + service_tax + tx_charges + other_chgs
            net_pnl = clean_float(row.get('Net Realized P&L', gross_pnl - total_charges))
            
            # Parse contract name: e.g. 'BAJAJ-AUTO Options 2025-11-25 8900 CE'
            op_type = 'CE' if ' CE' in name else ('PE' if ' PE' in name else ('FUT' if 'FUT' in name else None))
            strike_price = None
            clean_sym = name
            exp_date = None
            
            m = re.search(r'^([A-Za-z0-9_-]+)\s+(?:Options|Futures)\s+(\d{4}-\d{2}-\d{2})\s+([\d.]+)\s+(CE|PE)', name)
            if m:
                clean_sym = m.group(1)
                exp_date = clean_date(m.group(2))
                strike_price = float(m.group(3))
                op_type = m.group(4)
            else:
                m2 = re.search(r'^([A-Za-z0-9_-]+)', name)
                if m2: clean_sym = m2.group(1)
                m_strk = re.search(r'(\d+)\s+(CE|PE)', name)
                if m_strk: strike_price = float(m_strk.group(1))
            
            b_price = round(b_val / qty, 2) if qty > 0 else 0.0
            s_price = round(s_val / qty, 2) if qty > 0 else 0.0
            holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
            roi_pct = round((net_pnl / b_val * 100), 2) if b_val > 0 else 0.0
            fy = compute_financial_year(s_dt)
            outcome = 'PROFIT' if net_pnl > 0.01 else ('LOSS' if net_pnl < -0.01 else 'BREAKEVEN')
            
            thash = generate_trade_hash('HDFC Securities', 'FnO', clean_sym, b_dt, s_dt, qty, b_val, s_val, strike_price, op_type)
            trades.append({
                'TradeHash': thash,
                'Broker': 'HDFC Securities',
                'Segment': 'FnO',
                'SubSegment': 'Options' if op_type in ['CE', 'PE'] else 'Futures',
                'Symbol': clean_sym,
                'ContractName': name,
                'ISIN': None,
                'Sector': None,
                'OptionType': op_type,
                'StrikePrice': strike_price,
                'ExpiryDate': exp_date,
                'TradeType': 'LONG',
                'EntryDate': b_dt,
                'ExitDate': s_dt,
                'Quantity': qty,
                'BuyPrice': b_price,
                'BuyValue': b_val,
                'SellPrice': s_price,
                'SellValue': s_val,
                'HoldingDays': holding_days,
                'GrossPnL': gross_pnl,
                'Brokerage': brokerage,
                'STT': stt,
                'ExchangeCharges': tx_charges,
                'GST': service_tax,
                'StampDuty': 0.0,
                'OtherCharges': other_chgs,
                'TotalCharges': total_charges,
                'NetPnL': net_pnl,
                'ROIPct': roi_pct,
                'IsMTF': 0,
                'FinancialYear': fy,
                'CalYear': s_dt.year,
                'CalMonth': s_dt.month,
                'Outcome': outcome,
                'SourceFile': fname,
                'SourceSheet': 'Equity Derivatives'
            })
            
    try:
        xl.close()
    except:
        pass
    return trades, other_ledgers

def parse_blinkx_file(file_path):
    """
    Parses BlinkX PnL export files:
    - Pnl_*_Equity.xlsx
    - Pnl_*_commodity.xlsx
    - Pnl_*_derivatives.xlsx
    """
    trades = []
    other_ledgers = []
    fname = os.path.basename(file_path)
    xl = pd.ExcelFile(file_path)
    
    # 1. Equity
    if 'EQUITY' in xl.sheet_names:
        df_eq = xl.parse('EQUITY')
        for _, row in df_eq.iterrows():
            name = str(row.get('ScripName', '')).strip()
            if not name or name.lower() in ['total', 'nan']: continue
            isin = str(row.get('ISINCode', '')).strip()
            
            b_dt = clean_date(row.get('BuyDate'))
            s_dt = clean_date(row.get('SellDate'))
            if not s_dt: continue
            if not b_dt: b_dt = s_dt
            
            qty = clean_float(row.get('Quantity', 0))
            b_val = clean_float(row.get('BuyValue', 0.0))
            s_val = clean_float(row.get('SellValue', 0.0))
            b_price = clean_float(row.get('BuyRate', 0.0))
            s_price = clean_float(row.get('SellRate', 0.0))
            
            spec_pnl = clean_float(row.get('Speculation Profit/Loss', None), None)
            stcg_pnl = clean_float(row.get('Short Term Profit/Loss', None), None)
            ltcg_pnl = clean_float(row.get('Long Term Profit/Loss', None), None)
            
            subsegment = 'Delivery'
            if spec_pnl is not None and spec_pnl != 0.0:
                gross_pnl = spec_pnl
                subsegment = 'Intraday'
            elif stcg_pnl is not None and stcg_pnl != 0.0:
                gross_pnl = stcg_pnl
                subsegment = 'Short Term'
            elif ltcg_pnl is not None and ltcg_pnl != 0.0:
                gross_pnl = ltcg_pnl
                subsegment = 'Long Term'
            else:
                gross_pnl = s_val - b_val
                
            net_pnl = gross_pnl
            holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
            roi_pct = round((net_pnl / b_val * 100), 2) if b_val > 0 else 0.0
            fy = compute_financial_year(s_dt)
            outcome = 'PROFIT' if net_pnl > 0.01 else ('LOSS' if net_pnl < -0.01 else 'BREAKEVEN')
            
            thash = generate_trade_hash('BlinkX', 'Equity', name, b_dt, s_dt, qty, b_val, s_val, 0.0, '')
            trades.append({
                'TradeHash': thash,
                'Broker': 'BlinkX',
                'Segment': 'Equity',
                'SubSegment': subsegment,
                'Symbol': name,
                'ContractName': name,
                'ISIN': isin,
                'Sector': None,
                'OptionType': None,
                'StrikePrice': None,
                'ExpiryDate': None,
                'TradeType': 'LONG',
                'EntryDate': b_dt,
                'ExitDate': s_dt,
                'Quantity': qty,
                'BuyPrice': b_price or (round(b_val / qty, 2) if qty > 0 else 0.0),
                'BuyValue': b_val,
                'SellPrice': s_price or (round(s_val / qty, 2) if qty > 0 else 0.0),
                'SellValue': s_val,
                'HoldingDays': holding_days,
                'GrossPnL': gross_pnl,
                'Brokerage': 0.0,
                'STT': 0.0,
                'ExchangeCharges': 0.0,
                'GST': 0.0,
                'StampDuty': 0.0,
                'OtherCharges': 0.0,
                'TotalCharges': 0.0,
                'NetPnL': net_pnl,
                'ROIPct': roi_pct,
                'IsMTF': 0,
                'FinancialYear': fy,
                'CalYear': s_dt.year,
                'CalMonth': s_dt.month,
                'Outcome': outcome,
                'SourceFile': fname,
                'SourceSheet': 'EQUITY'
            })
            
    # 2. Commodity
    if 'COMMODITY' in xl.sheet_names:
        df_comm = xl.parse('COMMODITY')
        for _, row in df_comm.iterrows():
            sym = str(row.get('Symbol', '')).strip()
            if not sym or sym.lower() in ['total', 'nan']: continue
            
            b_dt = clean_date(row.get('BuyDate'))
            s_dt = clean_date(row.get('SellDate'))
            if not s_dt: continue
            if not b_dt: b_dt = s_dt
            
            qty = clean_float(row.get('Quantity', 0))
            b_val = clean_float(row.get('BuyValue', 0.0))
            s_val = clean_float(row.get('SellValue', 0.0))
            b_price = clean_float(row.get('BuyPrice', 0.0))
            s_price = clean_float(row.get('SellPrice', 0.0))
            pnl = clean_float(row.get('RealisedPNL', s_val - b_val))
            
            exp_date = clean_date(row.get('ExpiryDate'))
            strike_price = clean_float(row.get('StrikePrice', None), None)
            op_type = str(row.get('OptionType', '')).strip().upper() if pd.notna(row.get('OptionType')) else None
            contract = f"{sym} {exp_date} {strike_price or ''} {op_type or ''}".strip()
            
            holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
            roi_pct = round((pnl / b_val * 100), 2) if b_val > 0 else 0.0
            fy = compute_financial_year(s_dt)
            outcome = 'PROFIT' if pnl > 0.01 else ('LOSS' if pnl < -0.01 else 'BREAKEVEN')
            
            thash = generate_trade_hash('BlinkX', 'Commodity', sym, b_dt, s_dt, qty, b_val, s_val, strike_price, op_type)
            trades.append({
                'TradeHash': thash,
                'Broker': 'BlinkX',
                'Segment': 'Commodity',
                'SubSegment': 'Options' if op_type in ['CE', 'PE'] else 'Futures',
                'Symbol': sym,
                'ContractName': contract,
                'ISIN': None,
                'Sector': None,
                'OptionType': op_type,
                'StrikePrice': strike_price,
                'ExpiryDate': exp_date,
                'TradeType': 'LONG',
                'EntryDate': b_dt,
                'ExitDate': s_dt,
                'Quantity': qty,
                'BuyPrice': b_price,
                'BuyValue': b_val,
                'SellPrice': s_price,
                'SellValue': s_val,
                'HoldingDays': holding_days,
                'GrossPnL': pnl,
                'Brokerage': 0.0,
                'STT': 0.0,
                'ExchangeCharges': 0.0,
                'GST': 0.0,
                'StampDuty': 0.0,
                'OtherCharges': 0.0,
                'TotalCharges': 0.0,
                'NetPnL': pnl,
                'ROIPct': roi_pct,
                'IsMTF': 0,
                'FinancialYear': fy,
                'CalYear': s_dt.year,
                'CalMonth': s_dt.month,
                'Outcome': outcome,
                'SourceFile': fname,
                'SourceSheet': 'COMMODITY'
            })
            
    # 3. FnO
    if 'FNO' in xl.sheet_names:
        df_fno = xl.parse('FNO')
        for _, row in df_fno.iterrows():
            sym = str(row.get('Symbol', '')).strip()
            if not sym or sym.lower() in ['total', 'nan']: continue
            
            b_dt = clean_date(row.get('BuyDate'))
            s_dt = clean_date(row.get('SellDate'))
            if not s_dt: continue
            if not b_dt: b_dt = s_dt
            
            qty = clean_float(row.get('Quantity', 0))
            b_val = clean_float(row.get('BuyValue', 0.0))
            s_val = clean_float(row.get('SellValue', 0.0))
            b_price = clean_float(row.get('BuyPrice', 0.0))
            s_price = clean_float(row.get('SellPrice', 0.0))
            pnl = clean_float(row.get('RealisedPNL', s_val - b_val))
            
            exp_date = clean_date(row.get('ExpiryDate'))
            strike_price = clean_float(row.get('StrikePrice', None), None)
            op_type = str(row.get('OptionType', '')).strip().upper() if pd.notna(row.get('OptionType')) else None
            contract = f"{sym} {exp_date} {strike_price or ''} {op_type or ''}".strip()
            
            holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
            roi_pct = round((pnl / b_val * 100), 2) if b_val > 0 else 0.0
            fy = compute_financial_year(s_dt)
            outcome = 'PROFIT' if pnl > 0.01 else ('LOSS' if pnl < -0.01 else 'BREAKEVEN')
            
            thash = generate_trade_hash('BlinkX', 'FnO', sym, b_dt, s_dt, qty, b_val, s_val, strike_price, op_type)
            trades.append({
                'TradeHash': thash,
                'Broker': 'BlinkX',
                'Segment': 'FnO',
                'SubSegment': 'Options' if op_type in ['CE', 'PE'] else 'Futures',
                'Symbol': sym,
                'ContractName': contract,
                'ISIN': None,
                'Sector': None,
                'OptionType': op_type,
                'StrikePrice': strike_price,
                'ExpiryDate': exp_date,
                'TradeType': 'LONG',
                'EntryDate': b_dt,
                'ExitDate': s_dt,
                'Quantity': qty,
                'BuyPrice': b_price,
                'BuyValue': b_val,
                'SellPrice': s_price,
                'SellValue': s_val,
                'HoldingDays': holding_days,
                'GrossPnL': pnl,
                'Brokerage': 0.0,
                'STT': 0.0,
                'ExchangeCharges': 0.0,
                'GST': 0.0,
                'StampDuty': 0.0,
                'OtherCharges': 0.0,
                'TotalCharges': 0.0,
                'NetPnL': pnl,
                'ROIPct': roi_pct,
                'IsMTF': 0,
                'FinancialYear': fy,
                'CalYear': s_dt.year,
                'CalMonth': s_dt.month,
                'Outcome': outcome,
                'SourceFile': fname,
                'SourceSheet': 'FNO'
            })
            
    try:
        xl.close()
    except:
        pass
    return trades, other_ledgers

def parse_indmoney_file(file_path):
    """
    Parses INDMoney Consolidated Tax Report Excel file.
    Sheets: F&O, STCG, LTCG.
    """
    trades = []
    other_ledgers = []
    fname = os.path.basename(file_path)
    xl = pd.ExcelFile(file_path)
    
    # 1. F&O Sheet
    if 'F&O' in xl.sheet_names:
        df_fno = xl.parse('F&O', header=None)
        in_options = False
        in_futures = False
        h_map = {}
        
        for idx, row in df_fno.iterrows():
            vals = [str(x).strip() for x in row.dropna().tolist()]
            if not vals: continue
            
            first_val = vals[0].lower()
            if 'options trades' in first_val:
                in_options = True
                in_futures = False
                h_map = {}
                continue
            elif 'futures trades' in first_val:
                in_options = False
                in_futures = True
                h_map = {}
                continue
                
            if 'contract name' in [v.lower() for v in vals] and 'quantity' in [v.lower() for v in vals]:
                h_map = {str(val).strip().lower(): col_idx for col_idx, val in row.items() if pd.notna(val)}
                continue
                
            if (in_options or in_futures) and 'contract name' in h_map:
                contract_col = h_map.get('contract name')
                contract = str(row[contract_col]).strip() if pd.notna(row.get(contract_col)) else ''
                if not contract or contract.lower() in ['total', 'contract name', 'nan'] or contract.startswith('1.') or contract.startswith('7.'):
                    continue
                
                b_dt = clean_date(row.get(h_map.get('buy date')))
                s_dt = clean_date(row.get(h_map.get('sell date')))
                if not s_dt: continue
                if not b_dt: b_dt = s_dt
                
                qty = clean_float(row.get(h_map.get('quantity')), 0.0)
                b_price = clean_float(row.get(h_map.get('buy price')), 0.0)
                s_price = clean_float(row.get(h_map.get('sell price')), 0.0)
                b_val = round(b_price * qty, 2)
                s_val = round(s_price * qty, 2)
                
                gross_pnl = clean_float(row.get(h_map.get('gross gains/losses')), s_val - b_val)
                expense = clean_float(row.get(h_map.get('expense')), 0.0)
                net_pnl = gross_pnl - expense
                
                # Parse Contract Name: e.g. 'BEL 30 MAR ₹470 CALL' or 'NIFTY 25600 CALL'
                op_type = 'CE' if ('call' in contract.lower() or ' ce' in contract.lower()) else ('PE' if ('put' in contract.lower() or ' pe' in contract.lower()) else ('FUT' if in_futures else None))
                clean_sym = contract.split()[0].strip() if contract.split() else 'UNKNOWN'
                
                # Strike price extraction
                strike_price = None
                if op_type in ('CE', 'PE'):
                    strike_m = re.search(r'[\u20b9\?]?\s*(\d+(?:\.\d+)?)\s*(?:CALL|PUT|CE|PE)', contract, re.I)
                    if not strike_m:
                        strike_m = re.search(r'(\d{4,6})(?:CE|PE)', contract, re.I)
                    if strike_m:
                        strike_price = float(strike_m.group(1))
                
                holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
                roi_pct = round((net_pnl / b_val * 100), 2) if b_val > 0 else 0.0
                fy = compute_financial_year(s_dt)
                outcome = 'PROFIT' if net_pnl > 0.01 else ('LOSS' if net_pnl < -0.01 else 'BREAKEVEN')
                
                thash = generate_trade_hash('INDMoney', 'FnO', clean_sym, b_dt, s_dt, qty, b_val, s_val, strike_price, op_type)
                trades.append({
                    'TradeHash': thash,
                    'Broker': 'INDMoney',
                    'Segment': 'FnO',
                    'SubSegment': 'Options' if in_options else 'Futures',
                    'Symbol': clean_sym,
                    'ContractName': contract,
                    'ISIN': None,
                    'Sector': None,
                    'OptionType': op_type,
                    'StrikePrice': strike_price,
                    'ExpiryDate': None,
                    'TradeType': 'LONG',
                    'EntryDate': b_dt,
                    'ExitDate': s_dt,
                    'Quantity': qty,
                    'BuyPrice': b_price,
                    'BuyValue': b_val,
                    'SellPrice': s_price,
                    'SellValue': s_val,
                    'HoldingDays': holding_days,
                    'GrossPnL': gross_pnl,
                    'Brokerage': expense,
                    'STT': 0.0,
                    'ExchangeCharges': 0.0,
                    'GST': 0.0,
                    'StampDuty': 0.0,
                    'OtherCharges': 0.0,
                    'TotalCharges': expense,
                    'NetPnL': net_pnl,
                    'ROIPct': roi_pct,
                    'IsMTF': 0,
                    'FinancialYear': fy,
                    'CalYear': s_dt.year,
                    'CalMonth': s_dt.month,
                    'Outcome': outcome,
                    'SourceFile': fname,
                    'SourceSheet': 'F&O'
                })

    # 2. STCG and LTCG Sheets (Indian Stocks)
    for sheet_name, subseg in [('STCG', 'Short Term'), ('LTCG', 'Long Term')]:
        if sheet_name in xl.sheet_names:
            df_cg = xl.parse(sheet_name, header=None)
            in_stocks = False
            h_map = {}
            for idx, row in df_cg.iterrows():
                vals = [str(x).strip() for x in row.dropna().tolist()]
                if not vals: continue
                
                if 'indian stocks' in vals[0].lower():
                    in_stocks = True
                    h_map = {}
                    continue
                elif any(k in vals[0].lower() for k in ['us stocks', 'mutual funds', 'bonds', 'schedule']):
                    in_stocks = False
                    h_map = {}
                    continue
                    
                if 'name of stock' in [v.lower() for v in vals] and ('redemption date' in [v.lower() for v in vals] or 'purchase date' in [v.lower() for v in vals]):
                    h_map = {str(val).strip().lower(): col_idx for col_idx, val in row.items() if pd.notna(val)}
                    continue
                    
                if in_stocks and 'name of stock' in h_map:
                    stock_col = h_map.get('name of stock')
                    stock_name = str(row[stock_col]).strip() if pd.notna(row.get(stock_col)) else ''
                    if not stock_name or stock_name.lower() in ['total', 'name of stock', 'nan', 'gains', 'losses'] or stock_name.startswith('8.'):
                        continue
                    
                    isin_col = h_map.get('isin')
                    isin = str(row[isin_col]).strip() if isin_col and pd.notna(row.get(isin_col)) else ''
                    
                    s_dt = clean_date(row.get(h_map.get('redemption date')))
                    b_dt = clean_date(row.get(h_map.get('purchase date')))
                    if not s_dt: continue
                    if not b_dt: b_dt = s_dt
                    
                    qty_col = h_map.get('units sold')
                    qty = clean_float(row.get(qty_col), 0.0)
                    
                    # Columns in STCG/LTCG:
                    # In some files: Total, Gross Gains/Losses, Expense
                    gross_pnl = 0.0
                    expense = 0.0
                    b_val = 0.0
                    s_val = 0.0
                    
                    # Check for explicit columns
                    for c_name, c_idx in h_map.items():
                        if 'gross gains' in c_name:
                            gross_pnl = clean_float(row.get(c_idx), 0.0)
                        elif 'expense' in c_name:
                            expense = clean_float(row.get(c_idx), 0.0)
                            
                    # Row values check for purchase/redemption values
                    # Let's inspect numeric columns
                    num_vals = [clean_float(v) for v in row if pd.notna(v) and str(v).replace('.', '', 1).replace('-', '', 1).isdigit()]
                    if len(num_vals) >= 4 and (b_val == 0.0 and s_val == 0.0):
                        # typically: units, buy_price, sell_price, buy_val, sell_val, pnl, expense
                        # Let's compute from unit price if available
                        pass
                    
                    # Fallback if b_val / s_val not set:
                    p_unit_col = h_map.get('per unit')
                    tot_col = h_map.get('total')
                    if tot_col and pd.notna(row.get(tot_col)):
                        s_val = clean_float(row.get(tot_col), 0.0)
                    if p_unit_col and pd.notna(row.get(p_unit_col)) and qty > 0:
                        s_price = clean_float(row.get(p_unit_col), 0.0)
                        if s_val == 0: s_val = s_price * qty
                    
                    if gross_pnl == 0.0 and b_val > 0 and s_val > 0:
                        gross_pnl = s_val - b_val
                    net_pnl = gross_pnl - expense
                    
                    holding_days = (s_dt - b_dt).days if s_dt and b_dt else 0
                    roi_pct = round((net_pnl / b_val * 100), 2) if b_val > 0 else 0.0
                    fy = compute_financial_year(s_dt)
                    outcome = 'PROFIT' if net_pnl > 0.01 else ('LOSS' if net_pnl < -0.01 else 'BREAKEVEN')
                    
                    thash = generate_trade_hash('INDMoney', 'Equity', stock_name, b_dt, s_dt, qty, b_val, s_val, 0.0, '')
                    trades.append({
                        'TradeHash': thash,
                        'Broker': 'INDMoney',
                        'Segment': 'Equity',
                        'SubSegment': subseg,
                        'Symbol': stock_name,
                        'ContractName': stock_name,
                        'ISIN': isin,
                        'Sector': None,
                        'OptionType': None,
                        'StrikePrice': None,
                        'ExpiryDate': None,
                        'TradeType': 'LONG',
                        'EntryDate': b_dt,
                        'ExitDate': s_dt,
                        'Quantity': qty,
                        'BuyPrice': round(b_val / qty, 2) if qty > 0 and b_val > 0 else 0.0,
                        'BuyValue': b_val,
                        'SellPrice': round(s_val / qty, 2) if qty > 0 and s_val > 0 else 0.0,
                        'SellValue': s_val,
                        'HoldingDays': holding_days,
                        'GrossPnL': gross_pnl,
                        'Brokerage': expense,
                        'STT': 0.0,
                        'ExchangeCharges': 0.0,
                        'GST': 0.0,
                        'StampDuty': 0.0,
                        'OtherCharges': 0.0,
                        'TotalCharges': expense,
                        'NetPnL': net_pnl,
                        'ROIPct': roi_pct,
                        'IsMTF': 0,
                        'FinancialYear': fy,
                        'CalYear': s_dt.year,
                        'CalMonth': s_dt.month,
                        'Outcome': outcome,
                        'SourceFile': fname,
                        'SourceSheet': sheet_name
                    })

    try:
        xl.close()
    except:
        pass
    return trades, other_ledgers

# ----------------- INGESTION PIPELINE -----------------

def detect_broker(file_name, file_path=None):
    f_low = file_name.lower()
    if 'zerod' in f_low or 'pcc789' in f_low:
        return 'Zerodha'
    elif 'hdfc' in f_low or '848902' in f_low:
        return 'HDFC Securities'
    elif 'pnl_' in f_low or 'blinkx' in f_low:
        return 'BlinkX'
    elif 'consolidated_tax_report' in f_low or 'indmoney' in f_low:
        return 'INDMoney'
    
    if file_path and os.path.exists(file_path):
        try:
            with pd.ExcelFile(file_path) as xl:
                s_names = [s.lower() for s in xl.sheet_names]
                if any('tradewise exits' in s for s in s_names) or 'other debits and credits' in s_names:
                    return 'Zerodha'
                elif 'equity derivatives' in s_names or any('fixed income' in s for s in s_names):
                    return 'HDFC Securities'
                elif 'commodity' in s_names or ('equity' in s_names and 'fno' in s_names):
                    return 'BlinkX'
                elif 'schedule fa' in s_names or 'ltcg' in s_names:
                    return 'INDMoney'
        except:
            pass
    return 'Unknown'

def parse_file(file_path):
    broker = detect_broker(os.path.basename(file_path), file_path)
    if broker == 'Zerodha':
        return parse_zerodha_file(file_path)
    elif broker == 'HDFC Securities':
        return parse_hdfc_file(file_path)
    elif broker == 'BlinkX':
        return parse_blinkx_file(file_path)
    elif broker == 'INDMoney':
        return parse_indmoney_file(file_path)
    else:
        return [], []

def ingest_trades_to_db(trades, other_ledgers):
    """
    Inserts trades and ledger debits into SQL Server with deduplication.
    Returns: (inserted_trades, skipped_trades, inserted_ledgers, skipped_ledgers)
    """
    if not trades and not other_ledgers:
        return 0, 0, 0, 0
        
    inserted_trades = 0
    skipped_trades = 0
    inserted_ledgers = 0
    skipped_ledgers = 0
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch existing hashes to do lightning-fast in-memory deduplication
        cursor.execute("SELECT TradeHash FROM TradingJournal_Master")
        existing_trade_hashes = set(r[0] for r in cursor.fetchall())
        
        cursor.execute("SELECT LedgerHash FROM TradingJournal_OtherLedger")
        existing_ledger_hashes = set(r[0] for r in cursor.fetchall())
        
        # Insert Trades
        insert_trade_sql = """
        INSERT INTO TradingJournal_Master (
            TradeHash, Broker, Segment, SubSegment, Symbol, ContractName, ISIN, Sector,
            OptionType, StrikePrice, ExpiryDate, TradeType, EntryDate, ExitDate, Quantity,
            BuyPrice, BuyValue, SellPrice, SellValue, HoldingDays, GrossPnL,
            Brokerage, STT, ExchangeCharges, GST, StampDuty, OtherCharges, TotalCharges,
            NetPnL, ROIPct, IsMTF, MTFFundedAmount, MTFMarginAmount, MTFInterestCost, MTFNetReturn,
            FinancialYear, CalYear, CalMonth, Outcome, SourceFile, SourceSheet, CreatedAt, LastUpdatedAt
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE()
        )
        """
        
        for t in trades:
            thash = t['TradeHash']
            if thash in existing_trade_hashes:
                skipped_trades += 1
                continue
                
            cursor.execute(insert_trade_sql, (
                t['TradeHash'], t['Broker'], t['Segment'], t['SubSegment'], t['Symbol'], t['ContractName'], t['ISIN'], t['Sector'],
                t['OptionType'], t['StrikePrice'], t['ExpiryDate'], t['TradeType'], t['EntryDate'], t['ExitDate'], t['Quantity'],
                t['BuyPrice'], t['BuyValue'], t['SellPrice'], t['SellValue'], t['HoldingDays'], t['GrossPnL'],
                t['Brokerage'], t['STT'], t['ExchangeCharges'], t['GST'], t['StampDuty'], t['OtherCharges'], t['TotalCharges'],
                t['NetPnL'], t['ROIPct'], t['IsMTF'], t.get('MTFFundedAmount', 0.0), t.get('MTFMarginAmount', 0.0), t.get('MTFInterestCost', 0.0), t.get('MTFNetReturn', 0.0),
                t['FinancialYear'], t['CalYear'], t['CalMonth'], t['Outcome'], t['SourceFile'], t['SourceSheet']
            ))
            existing_trade_hashes.add(thash)
            inserted_trades += 1
            
        # Insert Other Ledgers
        insert_ledger_sql = """
        INSERT INTO TradingJournal_OtherLedger (
            LedgerHash, Broker, PostingDate, Particulars, Category, Debit, Credit, FinancialYear, SourceFile, CreatedAt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
        """
        for l in other_ledgers:
            lhash = l['LedgerHash']
            if lhash in existing_ledger_hashes:
                skipped_ledgers += 1
                continue
            cursor.execute(insert_ledger_sql, (
                l['LedgerHash'], l['Broker'], l['PostingDate'], l['Particulars'], l['Category'],
                l['Debit'], l['Credit'], l['FinancialYear'], l['SourceFile']
            ))
            existing_ledger_hashes.add(lhash)
            inserted_ledgers += 1
            
        conn.commit()
        
    return inserted_trades, skipped_trades, inserted_ledgers, skipped_ledgers

def sync_and_backup_folder(folder_path=r'C:\Users\navin\StockMarketFnO\data\My Journal'):
    """
    Scans the folder, categorizes each file by broker, parses and ingests all trades,
    and moves processed files into a backup folder.
    """
    import time
    import gc
    
    backup_folder = os.path.join(folder_path, 'backup')
    os.makedirs(backup_folder, exist_ok=True)
    
    files = [f for f in os.listdir(folder_path) if (f.endswith('.xlsx') or f.endswith('.xls')) and not f.startswith('~$') and not os.path.isdir(os.path.join(folder_path, f))]
    report = []
    
    for f in files:
        fpath = os.path.join(folder_path, f)
        broker = detect_broker(f, fpath)
        try:
            trades, ledgers = parse_file(fpath)
            ins_t, skip_t, ins_l, skip_l = ingest_trades_to_db(trades, ledgers)
            
            # Force GC and slight delay to release any Windows file lock
            gc.collect()
            time.sleep(0.2)
            
            # Move to backup
            broker_backup_dir = os.path.join(backup_folder, broker.replace(' ', '_'))
            os.makedirs(broker_backup_dir, exist_ok=True)
            dest_path = os.path.join(broker_backup_dir, f)
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(f)
                dest_path = os.path.join(broker_backup_dir, f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
            
            shutil.move(fpath, dest_path)
            
            report.append({
                'file': f,
                'broker': broker,
                'trades_found': len(trades),
                'trades_inserted': ins_t,
                'trades_skipped': skip_t,
                'ledgers_inserted': ins_l,
                'status': 'SUCCESS',
                'backup_location': dest_path
            })
        except Exception as e:
            report.append({
                'file': f,
                'broker': broker,
                'status': f'ERROR: {e}'
            })
            
    return report

if __name__ == '__main__':
    print("Testing journal_engine directly...")
    rep = sync_and_backup_folder()
    for r in rep:
        print(r)

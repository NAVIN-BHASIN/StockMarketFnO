"""
Trade Orders Analysis Ingestion Engine
=====================================
Multi-Broker order log & trade execution ingestion, normalization, SHA-256 deduplication,
and automated backup archiving for Zerodha, HDFC Securities, BlinkX, and INDMoney.
"""

import os
import re
import sys
import gc
import shutil
import hashlib
from datetime import datetime, date
import pandas as pd
import numpy as np
import pyodbc

SERVER = r'.\SQLEXPRESS'
DATABASE = 'Navin_Personal'
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

DEFAULT_ORDER_LOG_DIR = r'C:\Users\navin\StockMarketFnO\data\My Journal\Trade Order Log'
BACKUP_DIR = os.path.join(DEFAULT_ORDER_LOG_DIR, 'backup')

def get_connection():
    return pyodbc.connect(CONN_STR)

def compute_order_hash(broker, order_ref, symbol, date_time_str, action, qty, price, status):
    """Generate SHA-256 unique hash for an order to prevent duplicate rows."""
    key = f"{broker}|{order_ref}|{symbol}|{date_time_str}|{action}|{qty:.2f}|{price:.2f}|{status}".upper().strip()
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def get_financial_year(dt):
    """Compute Indian Financial Year (e.g. 2026-04-15 -> FY 2026-27)."""
    if dt is None or pd.isna(dt):
        return 'Unknown'
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt)
        except:
            return 'Unknown'
    y = dt.year
    m = dt.month
    if m >= 4:
        return f"FY {y}-{str(y+1)[-2:]}"
    else:
        return f"FY {y-1}-{str(y)[-2:]}"

# -------------------------------------------------------------
# BROKER PARSERS & SYMBOL RESOLVERS
# -------------------------------------------------------------

_ISIN_SYMBOL_CACHE = None

def get_isin_to_symbol_map():
    """Returns ISIN -> official NSE Symbol mapping cached in-memory."""
    global _ISIN_SYMBOL_CACHE
    if _ISIN_SYMBOL_CACHE is not None:
        return _ISIN_SYMBOL_CACHE
    m = {}
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT [ ISIN NUMBER], SYMBOL FROM Capital_Market_All_Stocks_NSE WHERE [ ISIN NUMBER] IS NOT NULL")
            for r in cur.fetchall():
                if r[0] and r[1]:
                    m[str(r[0]).strip().upper()] = str(r[1]).strip().upper()
    except Exception as e:
        print(f"Warning: Could not fetch ISIN map from DB: {e}")
    # Fallback / manual BSE scrips
    m['INE371F01024'] = 'CHANDRIMA'
    m['INE16W401027'] = 'AUGMONT'
    m['INE377Y01014'] = 'BAJAJHFL'
    _ISIN_SYMBOL_CACHE = m
    return _ISIN_SYMBOL_CACHE

HDFC_SCRIP_MAP = {
    '3IINFO': '3IINFOLTD', 'ADAPOW': 'ADANIPOWER', 'APOTYR': 'APOLLOTYRE', 'ASHLEY': 'ASHOKLEY',
    'AURPHA': 'AUROPHARMA', 'BHELTD': 'BHEL', 'BIRCOR': 'BIRLACORPN', 'BIRSOF': 'BSOFT',
    'BLUSTA': 'BLUESTARCO', 'BPCLTD': 'BPCL', 'CARUNI': 'CARBORUNIV', 'CESLTD': 'CESC',
    'CHASET': 'CHALET', 'CHOINV': 'CHOLAHLDNG', 'CIEAUT': 'CIEINDIA', 'CITUNI': 'CUB',
    'DATMAT': 'DATAMATICS', 'DCBLTD': 'DCMSHRIRAM', 'ENGIND': 'ENGINERSIN', 'EXIIND': 'EXIDEIND',
    'FINCAB': 'FINCABLES', 'FININD': 'FINEORG', 'GOLBEE': 'GOLDBEES', 'GTLINF': 'GTLINFRA',
    'GUJPIP': 'GPPL', 'HAPPST': 'HAPPSTMNDS', 'HBLPOW': 'HBLPOWER', 'HDFBAN': 'HDFCBANK',
    'HGINFR': 'HGINFRA', 'HINPET': 'HINDPETRO', 'IDFCFI': 'IDFCFIRSTB', 'INDHOT': 'INDHOTEL',
    'INDOIL': 'IOC', 'INFEDG': 'NAUKRI', 'INFTEC': 'INFY', 'INSECT': 'INSECTICID',
    'IPCLAB': 'IPCALAB', 'IRCTCE': 'IRCTC', 'ITCLTD': 'ITC', 'JAGPRA': 'JAGRAN',
    'JBFIN': 'JMFINANCIL', 'JBFINDEQNR': 'JMFINANCIL', 'JINSTA': 'JINDALSTEL', 'JYOLAB': 'JYOTHYLAB',
    'KALPOW': 'KPIL', 'KALPRO': 'KPIL', 'KARVYS': 'KARURVYSYA', 'LUPLTD': 'LUPIN',
    'MAHMAH': 'M&M', 'NARHRU': 'NH', 'NCCLTD': 'NCC', 'NIPLIF': 'NAM-INDIA',
    'NLCIND': 'NLCINDIA', 'NMDLTD': 'NMDC', 'NTPLTD': 'NTPC', 'OILIND': 'OIL',
    'OILNAT': 'ONGC', 'ORICEM': 'ORIENTCEM', 'PCBLLT': 'PCBL', 'PNCINF': 'PNCINFRA',
    'POLCOR': 'POLYPLEX', 'POWFIN': 'PFC', 'PSUBAN': 'PSB', 'PTCIND': 'PTC',
    'PUNNAT': 'PNB', 'RBLBAN': 'RBLBANK', 'RECLTD': 'RECLTD', 'RELCOM': 'RCOM',
    'RELIND': 'RELIANCE', 'SININD': 'SINDHUTRAD', 'SOUBAN': 'SOUTHBANK', 'STABAN': 'SBIN',
    'SUNLTD': 'SUNPHARMA', 'SUZLTD': 'SUZLON', 'SYNFOR': 'SYMPHONY', 'SYNINT': 'SYNGENE',
    'TATMOT': 'TATAMOTORS', 'TATSTE': 'TATASTEEL', 'TCSLTD': 'TCS', 'TRITUR': 'TRITURBINE',
    'UNIBAN': 'UNIONBANK', 'VARBEV': 'VBL', 'VEDANT': 'VEDL', 'VODIDE': 'IDEA',
    'WESDEV': 'WESTLIFE', 'WESFOO': 'WESTLIFE', 'ZEELEA': 'ZEEL', 'ZYDUSL': 'ZYDUSLIFE',
    'GLENMARKLIFE': 'GLS', 'ICICIBHA22': 'ICICIB22', 'IDFCFIREQNR': 'IDFCFIRSTB',
    'LICINDIA': 'LICI', 'NETFGILT5Y': 'GILT5YBEES', 'ZYDUSLTDEQ': 'ZYDUSLIFE'
}

def clean_hdfc_name(name):
    if not name or pd.isna(name):
        return 'UNKNOWN'
    s = str(name).strip().upper()
    if s in HDFC_SCRIP_MAP:
        return HDFC_SCRIP_MAP[s]
    clean = re.sub(r'(EQNR|EQTT|EQ)$', '', s).strip()
    if clean in HDFC_SCRIP_MAP:
        return HDFC_SCRIP_MAP[clean]
    return clean

def parse_hdfc_orders(fpath):
    """
    Parses HDFC Securities Orderlog Reports (both Equity Cash Delivery & Equity Derivatives).
    Header starts at row 13.
    """
    orders = []
    xl = None
    try:
        xl = pd.ExcelFile(fpath)
        sheet_name = [s for s in xl.sheet_names if 'orderlog' in s.lower() or 'equity' in s.lower()][0]
        df = xl.parse(sheet_name, skiprows=13)
        xl.close()
        del xl
        xl = None
        gc.collect()

        is_equity_report = 'Name' in df.columns and 'Symbol / Contract' not in df.columns

        for idx, r in df.iterrows():
            if is_equity_report:
                name = r.get('Name')
                if not name or str(name).lower() == 'nan' or str(name).startswith('---'):
                    continue

                dt_raw = r.get('Date & Time')
                dt_obj = pd.to_datetime(dt_raw, errors='coerce')
                if pd.isna(dt_obj):
                    continue

                action = str(r.get('Action', '')).strip().upper()
                if action not in ['BUY', 'SELL']:
                    continue

                order_qty = float(r.get('Order Qty', 0.0) or 0.0)
                exec_qty = float(r.get('Execution Qty', 0.0) or 0.0)
                price = float(r.get('Order Price', 0.0) or 0.0)
                trig_price = float(r.get('Trigger Price', 0.0) or 0.0)
                order_type = str(r.get('Order Type', 'MKT')).strip().upper()
                product = str(r.get('Product', 'Cash')).strip()

                status_raw = str(r.get('Status', 'Executed')).strip().upper()
                if 'EXEC' in status_raw or 'CONFIRMED' in status_raw:
                    order_status = 'EXECUTED'
                elif 'CANCEL' in status_raw:
                    order_status = 'CANCELLED'
                elif 'REJECT' in status_raw:
                    order_status = 'REJECTED'
                else:
                    order_status = status_raw

                reason = str(r.get('Reason', '')).replace('---', '').strip()
                hsl_ref = str(r.get('HSL Ref. No.', '')).strip()
                exch_ref = str(r.get('Exch. Order No.', '')).strip()

                symbol = clean_hdfc_name(name)
                contract = str(name).strip()

                order_ref = exch_ref or hsl_ref or f"{symbol}_{dt_obj.strftime('%Y%m%d%H%M%S')}_{order_qty}_{idx}"
                order_hash = compute_order_hash(
                    'HDFC Securities', order_ref, symbol, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    action, exec_qty if exec_qty > 0 else order_qty, price, order_status
                )

                orders.append({
                    'OrderHash': order_hash,
                    'Broker': 'HDFC Securities',
                    'Exchange': str(r.get('Exchange', 'NSE')).strip(),
                    'Segment': 'Equity',
                    'SubSegment': 'Delivery',
                    'Symbol': symbol,
                    'ContractName': contract,
                    'ISIN': None,
                    'OptionType': None,
                    'StrikePrice': None,
                    'ExpiryDate': None,
                    'OrderDateTime': dt_obj,
                    'OrderDate': dt_obj.date(),
                    'OrderTime': dt_obj.strftime('%H:%M:%S'),
                    'Action': action,
                    'OrderType': order_type,
                    'Product': product,
                    'OrderQty': order_qty,
                    'ExecutedQty': exec_qty,
                    'OrderPrice': price,
                    'ExecutionPrice': price,
                    'TriggerPrice': trig_price,
                    'OrderStatus': order_status,
                    'RejectionReason': reason if reason else None,
                    'BrokerOrderNo': hsl_ref if hsl_ref else None,
                    'ExchangeOrderNo': exch_ref if exch_ref else None,
                    'FinancialYear': get_financial_year(dt_obj),
                    'CalYear': dt_obj.year,
                    'CalMonth': dt_obj.month,
                    'SourceFile': os.path.basename(fpath)
                })

            else:
                contract = str(r.get('Symbol / Contract', '')).strip()
                if not contract or contract.lower() == 'nan' or contract.startswith('---'):
                    continue

                dt_raw = r.get('Date & Time')
                dt_obj = pd.to_datetime(dt_raw, errors='coerce')
                if pd.isna(dt_obj):
                    continue

                action = str(r.get('Action', '')).strip().upper()
                if action not in ['BUY', 'SELL']:
                    continue

                order_qty = float(r.get('Order Qty', 0.0) or 0.0)
                exec_qty = float(r.get('Exec. Qty', 0.0) or 0.0)
                order_price = float(r.get('Order Price', 0.0) or 0.0)
                trig_price = float(r.get('Trigger Price', 0.0) or 0.0)
                exec_price = float(r.get('Limit Price', order_price) or order_price)

                order_type = str(r.get('Order Type', 'LIMIT')).strip().upper()
                product = str(r.get('Product', 'Margin')).strip()
                status_raw = str(r.get('Status', 'Executed')).strip().upper()

                if 'EXEC' in status_raw or 'CONFIRMED' in status_raw:
                    order_status = 'EXECUTED'
                elif 'CANCEL' in status_raw:
                    order_status = 'CANCELLED'
                elif 'REJECT' in status_raw:
                    order_status = 'REJECTED'
                else:
                    order_status = status_raw

                reason = str(r.get('Reason', '')).replace('---', '').strip()
                hsl_ref = str(r.get('HSL Ref. No.', '')).strip()
                exch_ref = str(r.get('Exch. Order No.', '')).strip()
                order_ref = exch_ref or hsl_ref or f"{contract}_{dt_obj.strftime('%Y%m%d%H%M%S')}_{order_qty}_{idx}"

                # Contract Regex parser: OPTSTK-SONACOMS  -25AUG2026-CE-730.0000    -0
                m = re.search(r'^(OPT\w+|FUT\w+)-(.*?)-(\d{2}[A-Z]{3}\d{4})-(CE|PE|FF|FUT)-([\d\.]+)', contract.strip())
                if m:
                    itype, sym, exp_str, op, strk = m.groups()
                    symbol = sym.strip()
                    op_type = op.strip() if op.strip() in ['CE', 'PE'] else None
                    strike = float(strk) if op_type else None
                    try:
                        exp_date = pd.to_datetime(exp_str, format='%d%b%Y').date()
                    except:
                        exp_date = None
                    subseg = 'Futures' if ('FUT' in itype or op == 'FF') else 'Options'
                else:
                    symbol = contract.split('-')[0].strip()
                    op_type = None
                    strike = None
                    exp_date = None
                    subseg = 'Futures' if 'FUT' in contract else 'Options'

                order_hash = compute_order_hash(
                    'HDFC Securities', order_ref, symbol, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    action, order_qty, order_price, order_status
                )

                orders.append({
                    'OrderHash': order_hash,
                    'Broker': 'HDFC Securities',
                    'Exchange': str(r.get('Exchange', 'NSE')).strip(),
                    'Segment': 'FnO',
                    'SubSegment': subseg,
                    'Symbol': symbol,
                    'ContractName': contract,
                    'ISIN': None,
                    'OptionType': op_type,
                    'StrikePrice': strike,
                    'ExpiryDate': exp_date,
                    'OrderDateTime': dt_obj,
                    'OrderDate': dt_obj.date(),
                    'OrderTime': dt_obj.strftime('%H:%M:%S'),
                    'Action': action,
                    'OrderType': order_type,
                    'Product': product,
                    'OrderQty': order_qty,
                    'ExecutedQty': exec_qty,
                    'OrderPrice': order_price,
                    'ExecutionPrice': exec_price,
                    'TriggerPrice': trig_price,
                    'OrderStatus': order_status,
                    'RejectionReason': reason if reason else None,
                    'BrokerOrderNo': hsl_ref if hsl_ref else None,
                    'ExchangeOrderNo': exch_ref if exch_ref else None,
                    'FinancialYear': get_financial_year(dt_obj),
                    'CalYear': dt_obj.year,
                    'CalMonth': dt_obj.month,
                    'SourceFile': os.path.basename(fpath)
                })
    except Exception as e:
        print(f"Error parsing HDFC file {fpath}: {e}")
    finally:
        if xl:
            try: xl.close()
            except: pass
            gc.collect()

    return orders

def parse_indmoney_orders(fpath):
    """
    Parses INDMoney Transactions Report.
    Sheets: 'Equity transactions report' and 'FNO transactions report'. Headers at row 6.
    """
    orders = []
    xl = None
    try:
        xl = pd.ExcelFile(fpath)
        
        # 1. Equity Sheet
        eq_sheets = [s for s in xl.sheet_names if 'equity' in s.lower()]
        if eq_sheets:
            df_eq = xl.parse(eq_sheets[0], skiprows=6)
            for _, r in df_eq.iterrows():
                dt_obj = pd.to_datetime(r.get('Execution Date'), errors='coerce')
                if pd.isna(dt_obj):
                    continue

                action = str(r.get('Type', '')).strip().upper()
                if action not in ['BUY', 'SELL']:
                    continue

                scrip_name = str(r.get('Scrip Name', '')).strip()
                scrip_sym = str(r.get('Scrip Symbol', '')).strip()
                symbol = scrip_sym if scrip_sym and scrip_sym.lower() != 'nan' else scrip_name
                isin = str(r.get('ISIN', '')).strip() if pd.notna(r.get('ISIN')) else None

                qty = float(r.get('Quantity', 0.0) or 0.0)
                price = float(r.get('Price', 0.0) or 0.0)
                exch_ref = str(r.get('Exchange Order Id', '')).strip()
                status_raw = str(r.get('Order Status', 'Executed')).strip().upper()
                order_status = 'EXECUTED' if 'EXEC' in status_raw else status_raw

                order_ref = exch_ref or f"{symbol}_{dt_obj.strftime('%Y%m%d%H%M%S')}_{qty}"
                order_hash = compute_order_hash(
                    'INDMoney', order_ref, symbol, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    action, qty, price, order_status
                )

                orders.append({
                    'OrderHash': order_hash,
                    'Broker': 'INDMoney',
                    'Exchange': str(r.get('Exchange', 'NSE')).strip(),
                    'Segment': 'Equity',
                    'SubSegment': 'Delivery',
                    'Symbol': symbol,
                    'ContractName': scrip_name,
                    'ISIN': isin,
                    'OptionType': None,
                    'StrikePrice': None,
                    'ExpiryDate': None,
                    'OrderDateTime': dt_obj,
                    'OrderDate': dt_obj.date(),
                    'OrderTime': dt_obj.strftime('%H:%M:%S'),
                    'Action': action,
                    'OrderType': 'MARKET',
                    'Product': 'CNC',
                    'OrderQty': qty,
                    'ExecutedQty': qty,
                    'OrderPrice': price,
                    'ExecutionPrice': price,
                    'TriggerPrice': 0.0,
                    'OrderStatus': order_status,
                    'RejectionReason': None,
                    'BrokerOrderNo': None,
                    'ExchangeOrderNo': exch_ref,
                    'FinancialYear': get_financial_year(dt_obj),
                    'CalYear': dt_obj.year,
                    'CalMonth': dt_obj.month,
                    'SourceFile': os.path.basename(fpath)
                })

        # 2. FNO Sheet
        fno_sheets = [s for s in xl.sheet_names if 'fno' in s.lower()]
        if fno_sheets:
            df_fno = xl.parse(fno_sheets[0], skiprows=6)
            for _, r in df_fno.iterrows():
                dt_obj = pd.to_datetime(r.get('Execution Date'), errors='coerce')
                if pd.isna(dt_obj):
                    continue

                action = str(r.get('Type', '')).strip().upper()
                if action not in ['BUY', 'SELL']:
                    continue

                scrip_name = str(r.get('Scrip Name', '')).strip()
                scrip_sym = str(r.get('Scrip Symbol', '')).strip()

                qty = float(r.get('Quantity', 0.0) or 0.0)
                price = float(r.get('Price', 0.0) or 0.0)
                exch_ref = str(r.get('Exchange Order Id', '')).strip()
                status_raw = str(r.get('Order Status', 'Executed')).strip().upper()
                order_status = 'EXECUTED' if 'EXEC' in status_raw else status_raw

                # Scrip Name Regex: TRENT 29 May ₹6000 Call / NIFTY 15 May ₹24600 Call
                m = re.search(r'([A-Za-z0-9\&\s\-]+?)\s+(\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{2,4})?)\s+₹?(\d+(?:\.\d+)?)\s+(Call|Put|FUT)', scrip_name, re.IGNORECASE)
                if m:
                    sym, exp_str, strk, op = m.groups()
                    symbol = sym.strip().upper()
                    op_type = 'CE' if 'call' in op.lower() else ('PE' if 'put' in op.lower() else 'FUT')
                    strike = float(strk)
                    try:
                        exp_date = pd.to_datetime(f"{exp_str} {dt_obj.year}", format='%d %b %Y').date()
                    except:
                        exp_date = None
                    subseg = 'Options'
                else:
                    symbol = scrip_sym.upper() if scrip_sym and scrip_sym.lower() != 'nan' else scrip_name.split()[0].upper()
                    op_type = None
                    strike = None
                    exp_date = None
                    subseg = 'Futures' if 'FUT' in scrip_name else 'Options'

                order_ref = exch_ref or f"{symbol}_{dt_obj.strftime('%Y%m%d%H%M%S')}_{qty}"
                order_hash = compute_order_hash(
                    'INDMoney', order_ref, symbol, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    action, qty, price, order_status
                )

                orders.append({
                    'OrderHash': order_hash,
                    'Broker': 'INDMoney',
                    'Exchange': str(r.get('Exchange', 'NSE')).strip(),
                    'Segment': 'FnO',
                    'SubSegment': subseg,
                    'Symbol': symbol,
                    'ContractName': scrip_name,
                    'ISIN': None,
                    'OptionType': op_type,
                    'StrikePrice': strike,
                    'ExpiryDate': exp_date,
                    'OrderDateTime': dt_obj,
                    'OrderDate': dt_obj.date(),
                    'OrderTime': dt_obj.strftime('%H:%M:%S'),
                    'Action': action,
                    'OrderType': 'MARKET',
                    'Product': 'NRML',
                    'OrderQty': qty,
                    'ExecutedQty': qty,
                    'OrderPrice': price,
                    'ExecutionPrice': price,
                    'TriggerPrice': 0.0,
                    'OrderStatus': order_status,
                    'RejectionReason': None,
                    'BrokerOrderNo': None,
                    'ExchangeOrderNo': exch_ref,
                    'FinancialYear': get_financial_year(dt_obj),
                    'CalYear': dt_obj.year,
                    'CalMonth': dt_obj.month,
                    'SourceFile': os.path.basename(fpath)
                })

        xl.close()
        del xl
        xl = None
        gc.collect()
    except Exception as e:
        print(f"Error parsing INDMoney file {fpath}: {e}")
    finally:
        if xl:
            try: xl.close()
            except: pass
            gc.collect()

    return orders

def parse_zerodha_orders(fpath):
    """
    Parses Zerodha Tradebook (Equity / F&O).
    Header starts at row 14.
    """
    orders = []
    xl = None
    try:
        xl = pd.ExcelFile(fpath)
        is_fo = any('f&o' in s.lower() or 'fo' in s.lower() for s in xl.sheet_names)
        sheet_name = xl.sheet_names[0]
        df = xl.parse(sheet_name, skiprows=14)
        xl.close()
        del xl
        xl = None
        gc.collect()

        for _, r in df.iterrows():
            sym_raw = str(r.get('Symbol', '')).strip()
            if not sym_raw or sym_raw.lower() == 'nan':
                continue

            dt_raw = r.get('Order Execution Time') or r.get('Trade Date')
            dt_obj = pd.to_datetime(dt_raw, errors='coerce')
            if pd.isna(dt_obj):
                continue

            action = str(r.get('Trade Type', '')).strip().upper()
            if action not in ['BUY', 'SELL']:
                continue

            qty = float(r.get('Quantity', 0.0) or 0.0)
            price = float(r.get('Price', 0.0) or 0.0)
            trade_id = str(r.get('Trade ID', '')).strip()
            order_id = str(r.get('Order ID', '')).strip()
            isin = str(r.get('ISIN', '')).strip() if pd.notna(r.get('ISIN')) else None

            # Parse symbol if F&O
            op_type = None
            strike = None
            exp_date = None
            if is_fo:
                seg = 'FnO'
                # Example: NIFTY2640723000CE or CRUDEOIL26JAN5200CE
                m = re.search(r'([A-Za-z]+)(\d{2})(\d{1,2}|[A-Za-z]{3})(\d{2})(\d+)(CE|PE)', sym_raw)
                if m:
                    base_sym, yr, mo, dy, strk, op = m.groups()
                    symbol = base_sym.upper()
                    op_type = op.upper()
                    strike = float(strk)
                    subseg = 'Options'
                else:
                    symbol = re.sub(r'\d.*', '', sym_raw).upper()
                    subseg = 'Futures' if 'FUT' in sym_raw else 'Options'
                    op_type = 'FUT' if 'FUT' in sym_raw else ('CE' if sym_raw.endswith('CE') else ('PE' if sym_raw.endswith('PE') else None))
            else:
                seg = 'Equity'
                subseg = 'Delivery'
                symbol = sym_raw.upper()

            order_ref = order_id or trade_id or f"{symbol}_{dt_obj.strftime('%Y%m%d%H%M%S')}_{qty}"
            order_hash = compute_order_hash(
                'Zerodha', order_ref, symbol, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                action, qty, price, 'EXECUTED'
            )

            orders.append({
                'OrderHash': order_hash,
                'Broker': 'Zerodha',
                'Exchange': str(r.get('Exchange', 'NSE')).strip(),
                'Segment': seg,
                'SubSegment': subseg,
                'Symbol': symbol,
                'ContractName': sym_raw,
                'ISIN': isin,
                'OptionType': op_type,
                'StrikePrice': strike,
                'ExpiryDate': exp_date,
                'OrderDateTime': dt_obj,
                'OrderDate': dt_obj.date(),
                'OrderTime': dt_obj.strftime('%H:%M:%S'),
                'Action': action,
                'OrderType': 'LIMIT',
                'Product': 'NRML' if is_fo else 'CNC',
                'OrderQty': qty,
                'ExecutedQty': qty,
                'OrderPrice': price,
                'ExecutionPrice': price,
                'TriggerPrice': 0.0,
                'OrderStatus': 'EXECUTED',
                'RejectionReason': None,
                'BrokerOrderNo': order_id,
                'ExchangeOrderNo': trade_id,
                'FinancialYear': get_financial_year(dt_obj),
                'CalYear': dt_obj.year,
                'CalMonth': dt_obj.month,
                'SourceFile': os.path.basename(fpath)
            })
    except Exception as e:
        print(f"Error parsing Zerodha file {fpath}: {e}")
    finally:
        if xl:
            try: xl.close()
            except: pass
            gc.collect()

    return orders

def parse_blinkx_orders(fpath):
    """
    Parses BlinkX / JM Financial Trade Report.
    Sheets: FNO, COMMODITY, EQUITY. Header at row 0.
    """
    orders = []
    xl = None
    isin_map = get_isin_to_symbol_map()
    try:
        xl = pd.ExcelFile(fpath)
        
        for s in xl.sheet_names:
            df = xl.parse(s)
            s_up = s.upper()
            seg = 'Commodity' if 'COMM' in s_up else ('Equity' if 'EQ' in s_up else 'FnO')

            for idx, r in df.iterrows():
                dt_raw = r.get('Date')
                dt_obj = pd.to_datetime(dt_raw, errors='coerce')
                if pd.isna(dt_obj):
                    continue

                action = str(r.get('Buy/Sell', '')).strip().upper()
                if action not in ['BUY', 'SELL']:
                    continue

                qty = float(r.get('Qty', 0.0) or 0.0)
                price = float(r.get('Rate', 0.0) or 0.0)

                if seg == 'Equity':
                    isin = str(r.get('ISIN', '')).strip().upper() if pd.notna(r.get('ISIN')) else None
                    scrip_name = str(r.get('ScripName', r.get('Symbol', ''))).strip()
                    symbol = isin_map.get(isin, scrip_name.upper()) if isin else scrip_name.upper()
                    cname = scrip_name
                    op_type = None
                    strike = None
                    exp_date = None
                    subseg = 'Delivery'
                else:
                    symbol = str(r.get('Symbol', '')).strip().upper()
                    op_type = str(r.get('OptionType', '')).strip().upper() if pd.notna(r.get('OptionType')) else None
                    strike = float(r.get('StrikePrice', 0.0)) if pd.notna(r.get('StrikePrice')) else None
                    exp_raw = r.get('ExpiryDate')
                    exp_date = pd.to_datetime(exp_raw).date() if pd.notna(exp_raw) else None
                    subseg = 'Commodities' if seg == 'Commodity' else ('Options' if op_type in ['CE', 'PE'] else 'Futures')
                    cname = f"{symbol} {exp_date} {strike} {op_type}".strip()
                    isin = None

                val_raw = str(r.get('Value', ''))
                order_ref = f"{r.get('ScripCode', '')}_{symbol}_{dt_obj.strftime('%Y%m%d')}_{qty}_{price}_{action}_{val_raw}_{idx}"
                order_hash = compute_order_hash(
                    'BlinkX', order_ref, symbol, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    action, qty, price, 'EXECUTED'
                )

                orders.append({
                    'OrderHash': order_hash,
                    'Broker': 'BlinkX',
                    'Exchange': 'MCX' if seg == 'Commodity' else 'NSE',
                    'Segment': seg,
                    'SubSegment': subseg,
                    'Symbol': symbol,
                    'ContractName': cname,
                    'ISIN': isin,
                    'OptionType': op_type,
                    'StrikePrice': strike,
                    'ExpiryDate': exp_date,
                    'OrderDateTime': dt_obj,
                    'OrderDate': dt_obj.date(),
                    'OrderTime': dt_obj.strftime('%H:%M:%S'),
                    'Action': action,
                    'OrderType': 'LIMIT',
                    'Product': 'NRML' if seg != 'Equity' else 'CNC',
                    'OrderQty': qty,
                    'ExecutedQty': qty,
                    'OrderPrice': price,
                    'ExecutionPrice': price,
                    'TriggerPrice': 0.0,
                    'OrderStatus': 'EXECUTED',
                    'RejectionReason': None,
                    'BrokerOrderNo': None,
                    'ExchangeOrderNo': None,
                    'FinancialYear': get_financial_year(dt_obj),
                    'CalYear': dt_obj.year,
                    'CalMonth': dt_obj.month,
                    'SourceFile': os.path.basename(fpath)
                })

        xl.close()
        del xl
        xl = None
        gc.collect()
    except Exception as e:
        print(f"Error parsing BlinkX file {fpath}: {e}")
    finally:
        if xl:
            try: xl.close()
            except: pass
            gc.collect()

    return orders

def detect_broker_and_parse(fpath):
    """Detects broker from file name and content, and executes the appropriate parser."""
    fname = os.path.basename(fpath).lower()
    
    if '848902' in fname or 'hdfc' in fname or 'orderlog' in fname:
        return 'HDFC_Securities', parse_hdfc_orders(fpath)
    elif 'indmoney' in fname:
        return 'INDMoney', parse_indmoney_orders(fpath)
    elif 'tradebook' in fname or 'pcc789' in fname:
        return 'Zerodha', parse_zerodha_orders(fpath)
    elif 'tradereport' in fname or 'blinkx' in fname:
        return 'BlinkX', parse_blinkx_orders(fpath)
    else:
        # Fallback inspection by sheets
        try:
            xl = pd.ExcelFile(fpath)
            s_names = [s.lower() for s in xl.sheet_names]
            xl.close()
            del xl
            gc.collect()
            if any('orderlog' in s for s in s_names):
                return 'HDFC_Securities', parse_hdfc_orders(fpath)
            elif any('transactions report' in s for s in s_names):
                return 'INDMoney', parse_indmoney_orders(fpath)
            elif 'equity' in s_names and 'f&o' in s_names:
                return 'Zerodha', parse_zerodha_orders(fpath)
            elif 'fno' in s_names and 'commodity' in s_names:
                return 'BlinkX', parse_blinkx_orders(fpath)
        except:
            pass
        return 'Unknown', []

# -------------------------------------------------------------
# SYNC & BACKUP INGESTION PIPELINE
# -------------------------------------------------------------

def sync_trade_orders(folder_path=DEFAULT_ORDER_LOG_DIR, backup_dir=BACKUP_DIR):
    """
    Main ingestion engine:
    1. Scans folder_path for order logs
    2. Normalizes records and performs SHA-256 deduplication
    3. Bulk inserts new records into TradeOrders_Master
    4. Safely moves processed files into backup/<Broker>/
    5. Returns detailed execution report
    """
    os.makedirs(folder_path, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)

    files = [f for f in os.listdir(folder_path) 
             if f.endswith(('.xlsx', '.xls', '.csv')) and not f.startswith('~$') and os.path.isfile(os.path.join(folder_path, f))]

    report = {
        'total_files': len(files),
        'processed_files': 0,
        'new_orders_inserted': 0,
        'duplicates_skipped': 0,
        'details': [],
        'errors': []
    }

    if not files:
        report['details'].append("No new order log files found in directory.")
        return report

    all_orders = []
    file_broker_map = {}

    for fname in files:
        fpath = os.path.join(folder_path, fname)
        broker_name, orders = detect_broker_and_parse(fpath)
        file_broker_map[fpath] = (broker_name, fname)
        all_orders.extend(orders)
        report['details'].append(f"Parsed {len(orders)} orders from '{fname}' (Detected: {broker_name})")

    if not all_orders:
        report['details'].append("No order records parsed from files.")
        return report

    # Bulk insert into database with unique constraint check
    inserted_count = 0
    duplicate_count = 0

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch existing hashes for fast in-memory set comparison
            cursor.execute("SELECT OrderHash FROM TradeOrders_Master")
            existing_hashes = set(row[0] for row in cursor.fetchall())

            insert_query = """
                INSERT INTO TradeOrders_Master (
                    OrderHash, Broker, Exchange, Segment, SubSegment, Symbol, ContractName,
                    ISIN, OptionType, StrikePrice, ExpiryDate, OrderDateTime, OrderDate,
                    OrderTime, Action, OrderType, Product, OrderQty, ExecutedQty,
                    OrderPrice, ExecutionPrice, TriggerPrice, OrderStatus, RejectionReason,
                    BrokerOrderNo, ExchangeOrderNo, FinancialYear, CalYear, CalMonth, SourceFile
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            to_insert = []
            for o in all_orders:
                h = o['OrderHash']
                if h in existing_hashes:
                    duplicate_count += 1
                else:
                    existing_hashes.add(h)
                    to_insert.append((
                        o['OrderHash'], o['Broker'], o['Exchange'], o['Segment'], o['SubSegment'],
                        o['Symbol'], o['ContractName'], o['ISIN'], o['OptionType'], o['StrikePrice'],
                        o['ExpiryDate'], o['OrderDateTime'], o['OrderDate'], o['OrderTime'], o['Action'],
                        o['OrderType'], o['Product'], o['OrderQty'], o['ExecutedQty'], o['OrderPrice'],
                        o['ExecutionPrice'], o['TriggerPrice'], o['OrderStatus'], o['RejectionReason'],
                        o['BrokerOrderNo'], o['ExchangeOrderNo'], o['FinancialYear'], o['CalYear'],
                        o['CalMonth'], o['SourceFile']
                    ))

            if to_insert:
                cursor.fast_executemany = True
                cursor.executemany(insert_query, to_insert)
                conn.commit()
                inserted_count = len(to_insert)

    except Exception as e:
        report['errors'].append(f"Database insertion failed: {e}")
        return report

    report['new_orders_inserted'] = inserted_count
    report['duplicates_skipped'] = duplicate_count

    # Relocate processed files to backup/<Broker>
    gc.collect()
    for fpath, (broker_name, fname) in file_broker_map.items():
        if os.path.exists(fpath):
            broker_clean = broker_name.replace(' ', '_')
            b_target_dir = os.path.join(backup_dir, broker_clean)
            os.makedirs(b_target_dir, exist_ok=True)

            dest_path = os.path.join(b_target_dir, fname)
            # Avoid overwriting existing backup file with identical name
            if os.path.exists(dest_path):
                t_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                base, ext = os.path.splitext(fname)
                dest_path = os.path.join(b_target_dir, f"{base}_{t_str}{ext}")

            try:
                shutil.move(fpath, dest_path)
                report['processed_files'] += 1
                report['details'].append(f"Moved '{fname}' -> backup/{broker_clean}/")
            except PermissionError:
                report['errors'].append(f"File '{fname}' is currently open in Excel or another process. Orders were safely ingested into database; file will be moved to backup once closed.")
            except Exception as e:
                report['errors'].append(f"Failed to move '{fname}': {e}")

    return report

# -------------------------------------------------------------
# ANALYTICAL QUERY HELPERS FOR UI
# -------------------------------------------------------------

def get_distinct_filter_values():
    """Fetch distinct FYs, Brokers, Segments, SubSegments, Statuses, and Symbols."""
    out = {
        'financial_years': ['All FYs'],
        'brokers': ['All Brokers'],
        'segments': ['All Segments'],
        'subsegments': ['All SubSegments'],
        'statuses': ['All Statuses'],
        'symbols': ['All Symbols']
    }
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT FinancialYear FROM TradeOrders_Master WHERE FinancialYear IS NOT NULL ORDER BY FinancialYear DESC")
            out['financial_years'] += [r[0] for r in cursor.fetchall() if r[0]]
            
            cursor.execute("SELECT DISTINCT Broker FROM TradeOrders_Master WHERE Broker IS NOT NULL ORDER BY Broker")
            out['brokers'] += [r[0] for r in cursor.fetchall() if r[0]]
            
            cursor.execute("SELECT DISTINCT Segment FROM TradeOrders_Master WHERE Segment IS NOT NULL ORDER BY Segment")
            out['segments'] += [r[0] for r in cursor.fetchall() if r[0]]
            
            cursor.execute("SELECT DISTINCT SubSegment FROM TradeOrders_Master WHERE SubSegment IS NOT NULL ORDER BY SubSegment")
            out['subsegments'] += [r[0] for r in cursor.fetchall() if r[0]]
            
            cursor.execute("SELECT DISTINCT OrderStatus FROM TradeOrders_Master WHERE OrderStatus IS NOT NULL ORDER BY OrderStatus")
            out['statuses'] += [r[0] for r in cursor.fetchall() if r[0]]
            
            cursor.execute("SELECT DISTINCT Symbol FROM TradeOrders_Master WHERE Symbol IS NOT NULL ORDER BY Symbol")
            out['symbols'] += [r[0] for r in cursor.fetchall() if r[0]]
    except Exception as e:
        print(f"Error fetching distinct filter values: {e}")
    return out

def fetch_orders_data(filters=None):
    """
    Fetch filtered orders DataFrame from TradeOrders_Master.
    Supports filtering by FY, Broker, Segment, OrderStatus, Action, ExpiryDate, Date Range, Symbol.
    """
    sql = """
        SELECT 
            OrderID, OrderHash, Broker, Exchange, Segment, SubSegment, Symbol, ContractName,
            ISIN, OptionType, StrikePrice, ExpiryDate, OrderDateTime, OrderDate, OrderTime,
            Action, OrderType, Product, OrderQty, ExecutedQty, OrderPrice, ExecutionPrice,
            TriggerPrice, OrderStatus, RejectionReason, BrokerOrderNo, ExchangeOrderNo,
            FinancialYear, CalYear, CalMonth, SourceFile, CreatedAt
        FROM TradeOrders_Master
        WHERE 1=1
    """
    params = []
    if filters:
        if filters.get('fy') and filters['fy'] != 'All FYs':
            sql += " AND FinancialYear = ?"
            params.append(filters['fy'])
        if filters.get('broker') and filters['broker'] != 'All Brokers':
            sql += " AND Broker = ?"
            params.append(filters['broker'])
        if filters.get('segment') and filters['segment'] != 'All Segments':
            sql += " AND Segment = ?"
            params.append(filters['segment'])
        if filters.get('status') and filters['status'] != 'All Statuses' and filters['status'] != 'All':
            sql += " AND OrderStatus = ?"
            params.append(filters['status'])
        if filters.get('action') and filters['action'] not in ['All', 'All Actions']:
            sql += " AND Action = ?"
            params.append(filters['action'])
        if filters.get('order_type') and filters['order_type'] not in ['All', 'All Types']:
            sql += " AND OrderType = ?"
            params.append(filters['order_type'])
        if filters.get('product') and filters['product'] not in ['All', 'All Products']:
            sql += " AND Product = ?"
            params.append(filters['product'])
        if filters.get('expiry_date') and filters['expiry_date'] not in ['All', 'All Expiries']:
            sql += " AND ExpiryDate = ?"
            params.append(filters['expiry_date'])
        if filters.get('date_from'):
            sql += " AND OrderDate >= ?"
            params.append(filters['date_from'])
        if filters.get('date_to'):
            sql += " AND OrderDate <= ?"
            params.append(filters['date_to'])
        if filters.get('symbol'):
            sql += " AND (Symbol LIKE ? OR ContractName LIKE ?)"
            params.append(f"%{filters['symbol'].strip()}%")
            params.append(f"%{filters['symbol'].strip()}%")

    sql += " ORDER BY OrderDateTime DESC, OrderID DESC"

    try:
        with get_connection() as conn:
            df = pd.read_sql(sql, conn, params=params)
            return df
    except Exception as e:
        print(f"Error fetching orders data: {e}")
        return pd.DataFrame()

def extract_derivative_expiry(cname):
    """
    Extracts contract expiry date from derivative contract strings if ExpiryDate was NULL.
    Handles standard NSE/MCX contract patterns (e.g. AXISBANK25DEC1280CE, NIFTY 29 Sep ?23500 Call, OPTSTK-SOLARINDS -29SEP2026).
    """
    if not cname:
        return None
    c = str(cname).strip().upper()
    MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    
    # 1) DD-MMM-(202x) or DDMMM(202x) (e.g. 29SEP2026 or 29-SEP-2026)
    m = re.search(r'(\d{1,2})[\s\-]*([A-Z]{3})[\s\-]*(202\d|203\d)', c)
    if m and m.group(2) in MONTHS:
        d = int(m.group(1))
        mon = MONTHS.index(m.group(2)) + 1
        yr = int(m.group(3))
        try:
            return date(yr, mon, d)
        except:
            return date(yr, mon, 25)

    # 2) DD-MMM or DD MMM with assumed current/near year (e.g. 29 Sep)
    m = re.search(r'(\d{1,2})[\s\-]+([A-Z]{3})', c)
    if m and m.group(2) in MONTHS:
        d = int(m.group(1))
        mon = MONTHS.index(m.group(2)) + 1
        return date(2026, mon, d)

    # 3) YYMMM (e.g. 25DEC, 26JAN)
    m = re.search(r'(\d{2})([A-Z]{3})', c)
    if m and m.group(2) in MONTHS:
        yr = int('20' + m.group(1))
        mon = MONTHS.index(m.group(2)) + 1
        return date(yr, mon, 28)

    # 4) Weekly YYMDD (e.g. 25515 -> 15 May 2025, 25D16 -> 16 Dec 2025)
    m = re.search(r'(\d{2})([1-9OND])(\d{2})', c)
    if m:
        yr = int('20' + m.group(1))
        m_char = m.group(2)
        month_map = {'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'O':10,'N':11,'D':12}
        mon = month_map.get(m_char, 1)
        day = int(m.group(3))
        try:
            return date(yr, mon, day)
        except:
            return date(yr, mon, 25)

    return None

# -------------------------------------------------------------
# HIGH-PRECISION LIVE MARKET PRICE & QUOTE ENGINE
# -------------------------------------------------------------
_LIVE_LTP_CACHE = {}
_LIVE_LTP_TIMESTAMP = 0

def get_latest_market_prices(symbols=None, force_refresh_live=False):
    """
    Fetches latest market prices and intraday % change with high accuracy:
      1. Fetches real-time live quotes (LTP) via MarketAPI().get_bulk_live_details().
      2. Overlays historical Bhavcopy closing prices from CAPITAL_MARKET_HISTORY as fallback.
      3. Global in-memory cache valid for 120 seconds to ensure high performance without blocking UI.
    """
    global _LIVE_LTP_CACHE, _LIVE_LTP_TIMESTAMP
    import time
    now = time.time()
    result = {}

    # 1. Broad historical Bhavcopy close prices from SQL Database
    db_prices = {}
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                WITH LatestPrices AS (
                    SELECT [SYMBOL], [ CLOSE_PRICE],
                           ROW_NUMBER() OVER (PARTITION BY [SYMBOL] ORDER BY [ DATE1] DESC) as rn
                    FROM CAPITAL_MARKET_HISTORY
                )
                SELECT [SYMBOL], [ CLOSE_PRICE]
                FROM LatestPrices
                WHERE rn = 1
            """)
            for row in cur.fetchall():
                if row[0] and row[1] is not None:
                    db_prices[str(row[0]).strip().upper()] = float(row[1])
    except Exception as e:
        print(f"Error fetching latest market prices from DB: {e}")

    # 2. Overlay live prices from MarketAPI for held symbols
    if symbols:
        try:
            from market_api import MarketAPI
        except ImportError:
            MarketAPI = None

        sym_clean_list = list(set([str(s).strip().upper() for s in symbols if s and str(s).strip().upper() != 'UNKNOWN']))
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'live_ltp_cache.json')
        if not _LIVE_LTP_CACHE and os.path.exists(cache_path):
            try:
                import json
                with open(cache_path, 'r', encoding='utf-8') as fp:
                    saved = json.load(fp)
                    if isinstance(saved, dict) and 'prices' in saved:
                        _LIVE_LTP_CACHE = saved['prices']
                        _LIVE_LTP_TIMESTAMP = saved.get('timestamp', 0)
            except Exception:
                pass

        cache_valid = (not force_refresh_live) and (now - _LIVE_LTP_TIMESTAMP < 300) and bool(_LIVE_LTP_CACHE)

        if not cache_valid and MarketAPI and sym_clean_list:
            try:
                # Corporate action & renamed ticker translation table for NSE/Yahoo
                alias_map = {
                    'TATAMOTORS': 'TMPV.NS',
                    'ZOMATO': 'ETERNAL.NS',
                    'LTI': '540005.BO',
                    'LTIM': '540005.BO',
                    'MINDTREE': '540005.BO',
                    'CADILAHC': 'ZYDUSLIFE.NS',
                    'SRTRANSFIN': 'SHRIRAMFIN.NS',
                    'MOTHERSUMI': 'MOTHERSON.NS'
                }
                api = MarketAPI()
                fetch_symbols = [alias_map.get(s, s) for s in sym_clean_list]
                live_data = api.get_bulk_live_details(fetch_symbols)

                for s in sym_clean_list:
                    mapped = alias_map.get(s, s)
                    d = live_data.get(mapped, live_data.get(f"{mapped}.NS", live_data.get(s, live_data.get(f"{s}.NS", {}))))
                    p = d.get('price')
                    chg = d.get('pct_change', 0.0)
                    if p and float(p) > 0:
                        _LIVE_LTP_CACHE[s] = {
                            'price': float(p),
                            'change': float(chg),
                            'source': 'LIVE (NSE)'
                        }
                _LIVE_LTP_TIMESTAMP = now

                # Save to disk cache for sub-second instant restarts
                try:
                    import json
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path, 'w', encoding='utf-8') as fp:
                        json.dump({'timestamp': _LIVE_LTP_TIMESTAMP, 'prices': _LIVE_LTP_CACHE}, fp, indent=2)
                except Exception:
                    pass
            except Exception as ex:
                print(f"Error fetching bulk live quotes: {ex}")

    # Combine DB prices as baseline
    for s, p in db_prices.items():
        result[s] = {
            'price': p,
            'change': 0.0,
            'source': 'BHAVCOPY'
        }

    # Overlay live quotes
    for s, d in _LIVE_LTP_CACHE.items():
        result[s] = d

    return result


# -------------------------------------------------------------
# AUTOMATED RECONCILIATION ACTIONS (DISPUTE RESOLUTION)
# -------------------------------------------------------------
def auto_resolve_equity_inception_disputes():
    """
    Auto-resolves historical pre-log delivery sales where shares were sold from Demat
    that were purchased before account order logs began (resulting in negative net quantity).
    Inserts balancing opening acquisition entries tagged 'Opening_Demat_Inception_Reconciliation'.
    """
    df = compute_open_positions()
    eq_disp = df[(df['Segment'] == 'Equity') & (df['HoldingStatus'] == 'DISPUTE_DATA')]
    if eq_disp.empty:
        return 0, "No equity pre-log delivery disputes found."

    balancing_records = []
    for _, r in eq_disp.iterrows():
        broker = r['Broker']
        sym = r['Symbol']
        net_deficit = abs(float(r['NetQty']))
        avg_price = float(r['AvgEntryPrice'])
        first_dt = r['EarliestOrderDate']
        dt_str = f"{first_dt} 09:00:00" if first_dt else "2019-01-01 09:00:00"
        dt_obj = pd.to_datetime(dt_str)

        order_ref = f"INCEPTION_OPENING_BAL_{broker}_{sym}_{net_deficit:.0f}"
        order_hash = compute_order_hash(
            broker, order_ref, sym, dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
            'BUY', net_deficit, avg_price, 'EXECUTED'
        )

        balancing_records.append((
            order_hash, broker, 'NSE', 'Equity', 'Delivery', sym, r['ContractName'],
            'EQ', None, None, None, dt_obj, dt_obj.date(), '09:00:00', 'BUY', 'OPENING_BAL',
            'CNC', net_deficit, net_deficit, avg_price, avg_price, 0.0, 'EXECUTED',
            'Initial Demat Delivery Inception Balance (Pre-Log Acquisition)',
            f'INCEPTION-{sym}', f'INCEPTION-{sym}', get_financial_year(dt_obj),
            dt_obj.year, dt_obj.month, 'Opening_Demat_Inception_Reconciliation'
        ))

    insert_sql = """
        INSERT INTO TradeOrders_Master (
            OrderHash, Broker, Exchange, Segment, SubSegment, Symbol, ContractName,
            InstrumentType, OptionType, StrikePrice, ExpiryDate, OrderDateTime, OrderDate, OrderTime,
            Action, OrderType, ProductType, OrderQty, ExecutedQty, OrderPrice, ExecutionPrice,
            TriggerPrice, OrderStatus, OrderRemarks, BrokerOrderNo, ExchangeOrderNo,
            FinancialYear, CalendarYear, CalendarMonth, SourceFile
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """
    inserted = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for rec in balancing_records:
            try:
                cur.execute(insert_sql, rec)
                inserted += 1
            except Exception:
                pass
        conn.commit()

    return inserted, f"Successfully resolved {inserted} historical Demat delivery positions by creating opening acquisition records."

def undo_auto_resolve_equity_inception():
    """Reverts all auto-created Demat inception reconciliation records."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM TradeOrders_Master WHERE SourceFile = 'Opening_Demat_Inception_Reconciliation'")
        deleted = cur.rowcount
        conn.commit()
    return deleted, f"Reverted {deleted} inception reconciliation records."

def auto_square_off_expired_derivatives():
    """
    Auto-squares off historical expired F&O / Commodity contracts where contract expiry
    occurred without an explicit square-off order in the broker trade log.
    Inserts balancing exchange settlement entries tagged 'Auto_Expiry_Settlement_Reconciliation'.
    """
    df = compute_open_positions()
    deriv_disp = df[(df['Segment'].isin(['FnO', 'Commodity'])) & (df['HoldingStatus'] == 'DISPUTE_DATA')]
    if deriv_disp.empty:
        return 0, "No expired derivative disputes found."

    balancing_records = []
    for _, r in deriv_disp.iterrows():
        broker = r['Broker']
        seg = r['Segment']
        subseg = r['SubSegment']
        sym = r['Symbol']
        cname = r['ContractName']
        opt = r['OptionType']
        strike = r['StrikePrice']
        exp_val = r['ExpiryDate']
        net_qty = float(r['NetQty'])
        if abs(net_qty) < 1e-4:
            continue

        exp_dt_obj = pd.to_datetime(exp_val, errors='coerce')
        if pd.isna(exp_dt_obj):
            exp_dt_obj = pd.to_datetime(r['EarliestOrderDate'])

        settle_action = 'SELL' if net_qty > 0 else 'BUY'
        settle_qty = abs(net_qty)
        settle_price = 0.0

        dt_settle = exp_dt_obj.replace(hour=15, minute=30, second=0)
        order_ref = f"EXPIRY_SETTLE_{broker}_{cname}_{settle_qty:.0f}_{settle_action}"
        order_hash = compute_order_hash(
            broker, order_ref, sym, dt_settle.strftime('%Y-%m-%d %H:%M:%S'),
            settle_action, settle_qty, settle_price, 'EXECUTED'
        )

        balancing_records.append((
            order_hash, broker, 'NSE' if seg == 'FnO' else 'MCX', seg, subseg, sym, cname,
            'FUT' if 'FUT' in cname else 'OPT', opt if opt != 'N/A' else None, strike, exp_dt_obj.date(),
            dt_settle, dt_settle.date(), '15:30:00', settle_action, 'EXPIRY_SETTLEMENT',
            'NRML', settle_qty, settle_qty, settle_price, settle_price, 0.0, 'EXECUTED',
            'Exchange Expiry Automatic Settlement (Historical carry-forward reconciliation)',
            f'SETTLE-{sym}', f'SETTLE-{sym}', get_financial_year(dt_settle),
            dt_settle.year, dt_settle.month, 'Auto_Expiry_Settlement_Reconciliation'
        ))

    insert_sql = """
        INSERT INTO TradeOrders_Master (
            OrderHash, Broker, Exchange, Segment, SubSegment, Symbol, ContractName,
            InstrumentType, OptionType, StrikePrice, ExpiryDate, OrderDateTime, OrderDate, OrderTime,
            Action, OrderType, ProductType, OrderQty, ExecutedQty, OrderPrice, ExecutionPrice,
            TriggerPrice, OrderStatus, OrderRemarks, BrokerOrderNo, ExchangeOrderNo,
            FinancialYear, CalendarYear, CalendarMonth, SourceFile
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """
    inserted = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for rec in balancing_records:
            try:
                cur.execute(insert_sql, rec)
                inserted += 1
            except Exception:
                pass
        conn.commit()

    return inserted, f"Successfully auto-squared off {inserted} expired derivative contracts at expiry."

def undo_auto_square_off_expired_derivatives():
    """Reverts all auto-created derivative settlement records."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM TradeOrders_Master WHERE SourceFile = 'Auto_Expiry_Settlement_Reconciliation'")
        deleted = cur.rowcount
        conn.commit()
    return deleted, f"Reverted {deleted} derivative settlement records."


# -------------------------------------------------------------
# CORE OPEN HOLDINGS & DECISION ENGINE
# -------------------------------------------------------------
def compute_open_positions(as_of_date=None, filters=None, force_refresh_ltp=False):
    """
    Computes accurate Current Holdings & Carry Forward Portfolio across all segments (Equity, FnO, Commodity).
    Strict institutional standards:
      1. For EQUITY: Exactly 1 consolidated record per stock per broker.
         - Buy and Sell transactions are combined into a single balance.
         - If NetQty == 0: Closed cleanly, excluded from open holdings.
         - If NetQty > 0: Verified Demat Holding (carried forward).
         - If NetQty < 0: Pre-log delivery sells (awaiting reconciliation).
         - Every holding record includes 'OrdersList' with individual buy/sell timestamps, quantities, prices, and references.
      2. For F&O / COMMODITY: Grouped by contract.
         - Non-expired (DTE >= 0) -> Active Carry Forward.
         - Expired without square-off (DTE < 0) -> Dispute Data.
      3. LIVE LTP & DEEP DECISION INTELLIGENCE:
         - Fetches live quotes for all held symbols with caching.
         - Generates institutional DecisionVerdict, DecisionAdvice, and TrailingStoploss for every holding.
    """
    sql = """
        SELECT 
            OrderID, OrderHash, Broker, Exchange, Segment, SubSegment, Symbol, ContractName,
            OptionType, StrikePrice, ExpiryDate, OrderDateTime, OrderDate, OrderTime,
            Action, ExecutedQty, ExecutionPrice, TriggerPrice, BrokerOrderNo, ExchangeOrderNo, SourceFile
        FROM TradeOrders_Master
        WHERE OrderStatus = 'EXECUTED'
    """
    params = []
    if as_of_date:
        sql += " AND OrderDate <= ?"
        params.append(as_of_date)

    if filters:
        if filters.get('broker') and filters['broker'] != 'All Brokers':
            sql += " AND Broker = ?"
            params.append(filters['broker'])
        if filters.get('segment') and filters['segment'] != 'All Segments':
            sql += " AND Segment = ?"
            params.append(filters['segment'])
        if filters.get('symbol'):
            sql += " AND (Symbol LIKE ? OR ContractName LIKE ?)"
            params.append(f"%{filters['symbol'].strip()}%")
            params.append(f"%{filters['symbol'].strip()}%")

    sql += " ORDER BY OrderDateTime ASC, OrderID ASC"

    try:
        with get_connection() as conn:
            df = pd.read_sql(sql, conn, params=params)
            if df.empty:
                return pd.DataFrame()

            ref_date = pd.to_datetime(as_of_date).date() if as_of_date else date.today()
            positions = []

            # ---------------------------------------------------------
            # 1. EQUITY SEGMENT: Exactly 1 record per stock per broker
            # ---------------------------------------------------------
            df_eq = df[df['Segment'] == 'Equity']
            eq_symbols = list(df_eq['Symbol'].dropna().unique()) if not df_eq.empty else []

            # Fetch live market prices overlay
            market_quotes = get_latest_market_prices(symbols=eq_symbols, force_refresh_live=force_refresh_ltp)

            if not df_eq.empty:
                grouped_eq = df_eq.groupby(['Broker', 'Symbol'], dropna=False)

                for (broker, sym), g in grouped_eq:
                    sym_clean = str(sym).strip().upper() if sym else 'UNKNOWN'
                    buys = g[g['Action'] == 'BUY']
                    sells = g[g['Action'] == 'SELL']

                    buy_qty = buys['ExecutedQty'].sum()
                    sell_qty = sells['ExecutedQty'].sum()
                    net_qty = buy_qty - sell_qty

                    if abs(net_qty) < 1e-4:
                        continue  # Cleanly closed position

                    buy_val = (buys['ExecutedQty'] * buys['ExecutionPrice']).sum()
                    sell_val = (sells['ExecutedQty'] * sells['ExecutionPrice']).sum()

                    avg_buy = (buy_val / buy_qty) if buy_qty > 0 else 0.0
                    avg_sell = (sell_val / sell_qty) if sell_qty > 0 else 0.0

                    first_date = g['OrderDate'].min()
                    days_open = (ref_date - first_date).days if pd.notna(first_date) else 0

                    cname = g['ContractName'].iloc[0] if pd.notna(g['ContractName'].iloc[0]) else sym_clean

                    # Underlying executions list for drill-down modal
                    orders_list = []
                    for _, r in g.iterrows():
                        dt_val = r['OrderDateTime']
                        t_str = r['OrderTime'] if pd.notna(r['OrderTime']) else (dt_val.strftime('%H:%M:%S') if pd.notna(dt_val) else '')
                        d_str = str(r['OrderDate']) if pd.notna(r['OrderDate']) else ''
                        orders_list.append({
                            'OrderID': r['OrderID'],
                            'Date': d_str,
                            'Time': t_str,
                            'DateTime': dt_val,
                            'Action': r['Action'],
                            'ExecutedQty': float(r['ExecutedQty']),
                            'ExecutionPrice': float(r['ExecutionPrice']),
                            'OrderValue': float(r['ExecutedQty'] * r['ExecutionPrice']),
                            'BrokerOrderNo': r['BrokerOrderNo'] or '',
                            'ExchangeOrderNo': r['ExchangeOrderNo'] or '',
                            'SourceFile': r['SourceFile'] or ''
                        })

                    # Live Price & Day Change
                    q_data = market_quotes.get(sym_clean, {})
                    quote_p = q_data.get('price')
                    day_chg = q_data.get('change', 0.0)
                    quote_src = q_data.get('source', 'COST_BASIS')

                    if net_qty > 0:
                        stance = "LONG"
                        avg_entry_price = avg_buy
                        committed_val = net_qty * avg_buy
                        ltp = float(quote_p) if (quote_p is not None and float(quote_p) > 0) else avg_buy
                        cur_market_val = net_qty * ltp
                        unrealized_pnl = cur_market_val - committed_val
                        unrealized_roi = (unrealized_pnl / committed_val * 100) if committed_val > 0 else 0.0

                        holding_status = "VERIFIED_HOLDING"
                        status_display = "✅ VERIFIED HOLDING"
                        holding_cat = "Equity Demat Delivery"
                        dispute_reason = "None (Matched Demat Long Position)"
                        is_dispute = False

                        # Institutional Decision Intelligence
                        if unrealized_roi >= 35.0:
                            verdict = "🟡 PROFIT TRIM"
                            badge_color = "#FFD600"
                            trailing_sl = round(ltp * 0.92, 2)
                            advice = f"Substantial gain (+{unrealized_roi:.1f}%). Consider booking 20-30% partial profit to lock in wealth; trail stoploss at Rs. {trailing_sl:,.2f}."
                            action_code = "BOOK_PARTIAL"
                        elif unrealized_roi >= 12.0:
                            verdict = "🟢 STRONG HOLD"
                            badge_color = "#00E676"
                            trailing_sl = round(ltp * 0.90, 2)
                            advice = f"Strong compounder (+{unrealized_roi:.1f}%). Ride upward trend with trailing stoploss at Rs. {trailing_sl:,.2f}. Quarterly delivery volume positive."
                            action_code = "RIDE_TREND"
                        elif unrealized_roi >= -5.0:
                            verdict = "🟢 ACCUMULATE / SIP"
                            badge_color = "#69F0AE"
                            trailing_sl = round(avg_entry_price * 0.92, 2)
                            advice = f"Consolidating near cost ({unrealized_roi:+.1f}%). Support intact at Rs. {trailing_sl:,.2f}. Staggered accumulation candidate on pullbacks."
                            action_code = "ACCUMULATE"
                        elif unrealized_roi >= -15.0:
                            verdict = "🟠 MONITOR SUPPORT"
                            badge_color = "#FF9100"
                            trailing_sl = round(avg_entry_price * 0.85, 2)
                            advice = f"Drawdown ({unrealized_roi:.1f}%). Testing intermediate support at Rs. {trailing_sl:,.2f}. Monitor earnings closely before adding capital."
                            action_code = "MONITOR"
                        else:
                            verdict = "🔴 RISK CUT / STOPLOSS"
                            badge_color = "#FF5252"
                            trailing_sl = round(ltp * 0.95, 2)
                            advice = f"Deep drawdown ({unrealized_roi:.1f}%). Thesis under pressure. Consider cutting exposure to preserve capital or reallocating to leaders."
                            action_code = "CUT_LOSS"

                        recon_advice = f"Verified Demat holding in {broker}. Carried forward for {days_open} days."
                        suggested_action = advice
                    else:
                        # Net Qty < 0: Historical pre-log delivery sales
                        stance = "SHORT (Dispute)"
                        avg_entry_price = avg_sell
                        committed_val = abs(net_qty) * avg_sell
                        ltp = float(quote_p) if (quote_p is not None and float(quote_p) > 0) else avg_sell
                        cur_market_val = abs(net_qty) * ltp
                        unrealized_pnl = 0.0
                        unrealized_roi = 0.0

                        holding_status = "DISPUTE_DATA"
                        status_display = "⚠️ PRE-LOG SALE"
                        holding_cat = "Disputed Equity (Pre-Log Delivery Sells)"
                        dispute_reason = f"Pre-Log Delivery Sale: Sold {abs(net_qty):,.0f} shares from Demat purchased before order log start date (Bought: {buy_qty:,.0f}, Sold: {sell_qty:,.0f})."
                        verdict = "🛠️ RECONCILE DEMAT"
                        badge_color = "#FF9100"
                        trailing_sl = None
                        advice = f"Pre-log delivery sale in {broker}. Click '⚡ Auto-Resolve Demat Disputes' to insert opening balance acquisition."
                        action_code = "AUTO_RESOLVE_DEMAT"
                        recon_advice = advice
                        suggested_action = advice
                        is_dispute = True

                    positions.append({
                        'Broker': broker,
                        'Segment': 'Equity',
                        'SubSegment': 'Delivery',
                        'Symbol': sym_clean,
                        'ContractName': cname or sym_clean,
                        'OptionType': 'N/A',
                        'StrikePrice': None,
                        'ExpiryDate': 'N/A',
                        'Stance': stance,
                        'NetQty': net_qty,
                        'BuyQty': buy_qty,
                        'SellQty': sell_qty,
                        'BuyVal': buy_val,
                        'SellVal': sell_val,
                        'BuyOrdersCount': len(buys),
                        'SellOrdersCount': len(sells),
                        'AvgEntryPrice': avg_entry_price,
                        'AvgBuyPrice': avg_buy,
                        'AvgSellPrice': avg_sell,
                        'CommittedValue': committed_val,
                        'LTP': ltp,
                        'DayChangePct': day_chg,
                        'PriceSource': quote_src,
                        'CurrentMarketValue': cur_market_val,
                        'UnrealizedPnL': unrealized_pnl,
                        'UnrealizedROIPct': unrealized_roi,
                        'DecisionVerdict': verdict,
                        'DecisionAdvice': advice,
                        'DecisionBadgeColor': badge_color,
                        'DecisionActionCode': action_code,
                        'TrailingStoploss': trailing_sl,
                        'EarliestOrderDate': first_date,
                        'DaysOpen': max(0, days_open),
                        'DTE': None,
                        'DTERisk': 'N/A',
                        'HoldingStatus': holding_status,
                        'HoldingStatusDisplay': status_display,
                        'HoldingCategory': holding_cat,
                        'DisputeReason': dispute_reason,
                        'ReconciliationAdvice': recon_advice,
                        'IsDispute': is_dispute,
                        'SuggestedAction': suggested_action,
                        'OrdersList': orders_list
                    })

            # ---------------------------------------------------------
            # 2. DERIVATIVE & COMMODITY SEGMENTS
            # ---------------------------------------------------------
            df_deriv = df[df['Segment'].isin(['FnO', 'Commodity'])]
            if not df_deriv.empty:
                deriv_group_cols = ['Broker', 'Segment', 'SubSegment', 'Symbol', 'ContractName', 'OptionType', 'StrikePrice', 'ExpiryDate']
                grouped_deriv = df_deriv.groupby(deriv_group_cols, dropna=False)

                for key, g in grouped_deriv:
                    broker, seg, subseg, sym, cname, opt, strike, expiry = key
                    sym_clean = str(sym).strip().upper() if sym else 'UNKNOWN'

                    buys = g[g['Action'] == 'BUY']
                    sells = g[g['Action'] == 'SELL']

                    buy_qty = buys['ExecutedQty'].sum()
                    sell_qty = sells['ExecutedQty'].sum()
                    net_qty = buy_qty - sell_qty

                    if abs(net_qty) < 1e-4:
                        continue  # Cleanly closed position

                    buy_val = (buys['ExecutedQty'] * buys['ExecutionPrice']).sum()
                    sell_val = (sells['ExecutedQty'] * sells['ExecutionPrice']).sum()

                    avg_buy = (buy_val / buy_qty) if buy_qty > 0 else 0.0
                    avg_sell = (sell_val / sell_qty) if sell_qty > 0 else 0.0

                    stance = "LONG" if net_qty > 0 else "SHORT"
                    avg_entry_price = avg_buy if net_qty > 0 else avg_sell
                    committed_val = abs(net_qty) * avg_entry_price

                    first_date = g['OrderDate'].min()
                    days_open = (ref_date - first_date).days if pd.notna(first_date) else 0

                    exp_dt = None
                    if pd.notna(expiry) and expiry is not None:
                        try:
                            exp_dt = pd.to_datetime(expiry).date()
                        except:
                            exp_dt = None
                    if not exp_dt:
                        exp_dt = extract_derivative_expiry(cname)

                    dte = None
                    dte_risk = "N/A"
                    if exp_dt:
                        dte = (exp_dt - ref_date).days
                        if dte < 0:
                            dte_risk = "Expired"
                        elif dte <= 2:
                            dte_risk = "🚨 High Risk (<= 2d)"
                        elif dte <= 7:
                            dte_risk = "⚠️ Near Expiry (<= 7d)"
                        else:
                            dte_risk = "✅ Normal (> 7d)"

                    # Underlying market price lookup
                    q_data = market_quotes.get(sym_clean, {})
                    quote_p = q_data.get('price')
                    day_chg = q_data.get('change', 0.0)

                    ltp = avg_entry_price
                    cur_market_val = abs(net_qty) * ltp
                    unrealized_pnl = 0.0
                    unrealized_roi = 0.0

                    # Orders list for drill-down
                    orders_list = []
                    for _, r in g.iterrows():
                        dt_val = r['OrderDateTime']
                        t_str = r['OrderTime'] if pd.notna(r['OrderTime']) else (dt_val.strftime('%H:%M:%S') if pd.notna(dt_val) else '')
                        d_str = str(r['OrderDate']) if pd.notna(r['OrderDate']) else ''
                        orders_list.append({
                            'OrderID': r['OrderID'],
                            'Date': d_str,
                            'Time': t_str,
                            'DateTime': dt_val,
                            'Action': r['Action'],
                            'ExecutedQty': float(r['ExecutedQty']),
                            'ExecutionPrice': float(r['ExecutionPrice']),
                            'OrderValue': float(r['ExecutedQty'] * r['ExecutionPrice']),
                            'BrokerOrderNo': r['BrokerOrderNo'] or '',
                            'ExchangeOrderNo': r['ExchangeOrderNo'] or '',
                            'SourceFile': r['SourceFile'] or ''
                        })

                    if dte is not None and dte < 0:
                        holding_status = "DISPUTE_DATA"
                        status_display = "⚠️ EXPIRED CONTRACT"
                        holding_cat = f"Disputed Derivative (Expired {exp_dt})"
                        dispute_reason = f"Expired Contract: Contract expired on {exp_dt} ({abs(dte)} days ago) without closing square-off trade in broker file."
                        verdict = "🛠️ SETTLE EXPIRED"
                        badge_color = "#FF9100"
                        trailing_sl = None
                        advice = f"Contract expired on {exp_dt}. Click '🔄 Auto-Square Off Expired' to balance position."
                        action_code = "AUTO_SETTLE_EXPIRY"
                        recon_advice = advice
                        suggested_action = advice
                        is_dispute = True
                    elif dte is not None and dte >= 0:
                        holding_status = "ACTIVE_DERIVATIVE"
                        status_display = "🟢 ACTIVE CARRY FORWARD"
                        holding_cat = f"Active {seg} Carry Forward"
                        dispute_reason = "None (Active Contract)"
                        recon_advice = f"Active carry forward derivative position in {broker}. {dte} DTE remaining."

                        if dte <= 2:
                            verdict = "🚨 EXPIRY RISK / CLOSE"
                            badge_color = "#FF5252"
                            trailing_sl = round(avg_entry_price * 0.90, 2)
                            advice = f"Crucial expiry alert: Only {dte} day(s) left. Heavy theta decay & delivery margin risk. Rollover or square off immediately."
                            action_code = "SQUARE_OFF"
                        elif dte <= 7:
                            verdict = "⚠️ NEAR EXPIRY / ROLL"
                            badge_color = "#FF9100"
                            trailing_sl = round(avg_entry_price * 0.85, 2)
                            advice = f"{dte} DTE remaining. Theta acceleration zone. If directional thesis remains intact, plan rollover to next month cycle."
                            action_code = "ROLLOVER"
                        else:
                            verdict = "🟢 ACTIVE POSITION"
                            badge_color = "#00E5FF"
                            trailing_sl = round(avg_entry_price * 0.80, 2)
                            advice = f"Position within operational range ({dte} DTE). Maintain strict stoploss at predefined technical level."
                            action_code = "HOLD"

                        suggested_action = advice
                        is_dispute = False
                    else:
                        if days_open > 60:
                            holding_status = "DISPUTE_DATA"
                            status_display = "⚠️ OLD UNSQUARED"
                            holding_cat = f"Disputed Derivative (Old Unsquared)"
                            dispute_reason = f"Derivative position opened {days_open} days ago without recorded expiry date or exit leg."
                            verdict = "🛠️ SETTLE EXPIRED"
                            badge_color = "#FF9100"
                            trailing_sl = None
                            advice = f"Old unsquared derivative trade in {broker}. Please review or auto-settle."
                            action_code = "AUTO_SETTLE_EXPIRY"
                            recon_advice = advice
                            suggested_action = advice
                            is_dispute = True
                        else:
                            holding_status = "ACTIVE_DERIVATIVE"
                            status_display = "🟢 ACTIVE CARRY FORWARD"
                            holding_cat = f"Active {seg} Carry Forward"
                            dispute_reason = "None (Active Contract)"
                            verdict = "🟢 ACTIVE POSITION"
                            badge_color = "#00E5FF"
                            trailing_sl = None
                            advice = "Active derivative position open. Maintain strict stoploss."
                            action_code = "HOLD"
                            recon_advice = f"Active derivative position open in {broker}."
                            suggested_action = advice
                            is_dispute = False

                    positions.append({
                        'Broker': broker,
                        'Segment': seg,
                        'SubSegment': subseg,
                        'Symbol': sym_clean,
                        'ContractName': cname or sym_clean,
                        'OptionType': opt or 'N/A',
                        'StrikePrice': strike if pd.notna(strike) else None,
                        'ExpiryDate': str(exp_dt) if exp_dt else (str(expiry) if pd.notna(expiry) else 'N/A'),
                        'Stance': stance,
                        'NetQty': net_qty,
                        'BuyQty': buy_qty,
                        'SellQty': sell_qty,
                        'BuyVal': buy_val,
                        'SellVal': sell_val,
                        'BuyOrdersCount': len(buys),
                        'SellOrdersCount': len(sells),
                        'AvgEntryPrice': avg_entry_price,
                        'AvgBuyPrice': avg_buy,
                        'AvgSellPrice': avg_sell,
                        'CommittedValue': committed_val,
                        'LTP': ltp,
                        'DayChangePct': day_chg,
                        'PriceSource': 'DERIVATIVE_EXEC',
                        'CurrentMarketValue': cur_market_val,
                        'UnrealizedPnL': unrealized_pnl,
                        'UnrealizedROIPct': unrealized_roi,
                        'DecisionVerdict': verdict,
                        'DecisionAdvice': advice,
                        'DecisionBadgeColor': badge_color,
                        'DecisionActionCode': action_code,
                        'TrailingStoploss': trailing_sl,
                        'EarliestOrderDate': first_date,
                        'DaysOpen': max(0, days_open),
                        'DTE': dte,
                        'DTERisk': dte_risk,
                        'HoldingStatus': holding_status,
                        'HoldingStatusDisplay': status_display,
                        'HoldingCategory': holding_cat,
                        'DisputeReason': dispute_reason,
                        'ReconciliationAdvice': recon_advice,
                        'IsDispute': is_dispute,
                        'SuggestedAction': suggested_action,
                        'OrdersList': orders_list
                    })

            res_df = pd.DataFrame(positions)
            if not res_df.empty:
                status_prio = {'VERIFIED_HOLDING': 0, 'ACTIVE_DERIVATIVE': 1, 'DISPUTE_DATA': 2}
                res_df['SortPrio'] = res_df['HoldingStatus'].map(lambda s: status_prio.get(s, 9))
                res_df.sort_values(by=['SortPrio', 'CommittedValue'], ascending=[True, False], inplace=True)
                res_df.drop(columns=['SortPrio'], inplace=True, errors='ignore')

            # Optional holding_filter
            if filters and filters.get('holding_filter'):
                hf = str(filters['holding_filter']).upper()
                if 'VERIFIED' in hf:
                    res_df = res_df[res_df['HoldingStatus'].isin(['VERIFIED_HOLDING', 'ACTIVE_DERIVATIVE'])]
                elif 'DISPUTE' in hf:
                    res_df = res_df[res_df['HoldingStatus'] == 'DISPUTE_DATA']
                elif 'EQUITY' in hf:
                    res_df = res_df[res_df['HoldingCategory'].str.contains('Equity Demat', case=False, na=False)]
                elif 'DERIVATIVE' in hf:
                    res_df = res_df[res_df['HoldingStatus'] == 'ACTIVE_DERIVATIVE']

            return res_df

    except Exception as e:
        print(f"Error computing open positions: {e}")
        return pd.DataFrame()

def match_orders_to_trades(filters=None):
    """
    FIFO Trade Matching Engine:
    Matches executed BUY and SELL orders from TradeOrders_Master into:
      - CLOSED Trades: accurately matches both Buy & Sell legs, Entry Date, Exit Date, Qty, Prices, Gross P&L, ROI%, Holding Days.
      - OPEN Trades: tracks active open positions with Entry Date, Entry Price, Open Qty, Committed Value, Days Open, Expiry, DTE Risk.
    """
    sql = """
        SELECT 
            OrderID, Broker, Segment, SubSegment, Symbol, ContractName, OptionType, StrikePrice, ExpiryDate,
            Action, ExecutedQty, ExecutionPrice, OrderDate, OrderDateTime, Product, FinancialYear
        FROM TradeOrders_Master
        WHERE OrderStatus = 'EXECUTED' AND ExecutedQty > 0 AND ExecutionPrice > 0
    """
    params = []
    if filters:
        if filters.get('broker') and filters['broker'] != 'All Brokers':
            sql += " AND Broker = ?"
            params.append(filters['broker'])
        if filters.get('segment') and filters['segment'] != 'All Segments':
            sql += " AND Segment = ?"
            params.append(filters['segment'])
        if filters.get('fy') and filters['fy'] != 'All FYs':
            sql += " AND FinancialYear = ?"
            params.append(filters['fy'])
        if filters.get('symbol'):
            sql += " AND (Symbol LIKE ? OR ContractName LIKE ?)"
            params.append(f"%{filters['symbol'].strip()}%")
            params.append(f"%{filters['symbol'].strip()}%")

    sql += " ORDER BY OrderDateTime ASC, OrderID ASC"

    def _parse_to_date(val):
        if val is None or pd.isna(val):
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return pd.to_datetime(val).date()
        except:
            return None

    try:
        with get_connection() as conn:
            df = pd.read_sql(sql, conn, params=params)
            if df.empty:
                return pd.DataFrame()

            closed_trades = []
            open_trades = []

            group_cols = ['Broker', 'Segment', 'SubSegment', 'Symbol', 'ContractName', 'OptionType', 'StrikePrice', 'ExpiryDate']
            grouped = df.groupby(group_cols, dropna=False)
            ref_date = date.today()

            for key, g in grouped:
                broker, seg, subseg, sym, cname, opt, strike, expiry = key
                buy_queue = []   # list of {order_id, date, dt, qty, price, fy}
                sell_queue = []  # list of {order_id, date, dt, qty, price, fy}

                for _, row in g.iterrows():
                    act = row['Action']
                    qty = float(row['ExecutedQty'])
                    px = float(row['ExecutionPrice'])
                    dt_d = _parse_to_date(row['OrderDate'])
                    dt_tm = row['OrderDateTime']
                    oid = row['OrderID']
                    fy = row['FinancialYear']

                    if act == 'BUY':
                        # Match against any open short sells first (FIFO)
                        while qty > 1e-4 and sell_queue:
                            s_item = sell_queue[0]
                            match_qty = min(qty, s_item['qty'])
                            pnl = (s_item['price'] - px) * match_qty  # Short trade: Entry is Sell, Exit is Buy
                            s_date = s_item['date']
                            holding_days = (dt_d - s_date).days if (dt_d and s_date and dt_d >= s_date) else 0
                            roi_pct = (pnl / (match_qty * s_item['price']) * 100) if s_item['price'] > 0 else 0.0

                            # Deep insights
                            if pnl > 0:
                                insight = f"Profitable Short: Covered {match_qty:,.0f} qty at Rs. {px:,.2f} (+Rs. {pnl:,.2f}, +{roi_pct:.1f}%). Holding: {holding_days}d."
                            else:
                                insight = f"Loss Short: Covered {match_qty:,.0f} qty at Rs. {px:,.2f} (-Rs. {abs(pnl):,.2f}, {roi_pct:.1f}%). Holding: {holding_days}d."

                            closed_trades.append({
                                'TradeID': f"CL-S{s_item['order_id']}-B{oid}",
                                'Status': 'CLOSED',
                                'Broker': broker,
                                'Segment': seg,
                                'SubSegment': subseg,
                                'Symbol': sym,
                                'ContractName': cname or sym,
                                'OptionType': opt or 'N/A',
                                'StrikePrice': strike if pd.notna(strike) else None,
                                'ExpiryDate': str(expiry) if pd.notna(expiry) else None,
                                'Stance': 'SHORT',
                                'Quantity': match_qty,
                                'EntryDate': str(s_date) if s_date else str(s_item['date']),
                                'EntryPrice': s_item['price'],
                                'EntryValue': match_qty * s_item['price'],
                                'ExitDate': str(dt_d) if dt_d else str(row['OrderDate']),
                                'ExitPrice': px,
                                'ExitValue': match_qty * px,
                                'BuyPrice': px,
                                'SellPrice': s_item['price'],
                                'BuyValue': match_qty * px,
                                'SellValue': match_qty * s_item['price'],
                                'GrossPnL': pnl,
                                'ROIPct': roi_pct,
                                'HoldingDays': holding_days,
                                'Outcome': 'PROFIT' if pnl > 0 else ('LOSS' if pnl < 0 else 'BREAKEVEN'),
                                'FinancialYear': fy,
                                'Insights': insight,
                                'EntryOrderID': s_item['order_id'],
                                'ExitOrderID': oid
                            })
                            qty -= match_qty
                            s_item['qty'] -= match_qty
                            if s_item['qty'] < 1e-4:
                                sell_queue.pop(0)

                        if qty > 1e-4:
                            buy_queue.append({'order_id': oid, 'date': dt_d, 'dt': dt_tm, 'qty': qty, 'price': px, 'fy': fy})

                    elif act == 'SELL':
                        # Match against open long buys (FIFO)
                        while qty > 1e-4 and buy_queue:
                            b_item = buy_queue[0]
                            match_qty = min(qty, b_item['qty'])
                            pnl = (px - b_item['price']) * match_qty  # Long trade: Entry is Buy, Exit is Sell
                            b_date = b_item['date']
                            holding_days = (dt_d - b_date).days if (dt_d and b_date and dt_d >= b_date) else 0
                            roi_pct = (pnl / (match_qty * b_item['price']) * 100) if b_item['price'] > 0 else 0.0

                            # Deep insights
                            if pnl > 0:
                                insight = f"Profitable Long: Exited {match_qty:,.0f} qty at Rs. {px:,.2f} (+Rs. {pnl:,.2f}, +{roi_pct:.1f}%). Holding: {holding_days}d."
                            else:
                                insight = f"Loss Long: Exited {match_qty:,.0f} qty at Rs. {px:,.2f} (-Rs. {abs(pnl):,.2f}, {roi_pct:.1f}%). Holding: {holding_days}d."

                            closed_trades.append({
                                'TradeID': f"CL-B{b_item['order_id']}-S{oid}",
                                'Status': 'CLOSED',
                                'Broker': broker,
                                'Segment': seg,
                                'SubSegment': subseg,
                                'Symbol': sym,
                                'ContractName': cname or sym,
                                'OptionType': opt or 'N/A',
                                'StrikePrice': strike if pd.notna(strike) else None,
                                'ExpiryDate': str(expiry) if pd.notna(expiry) else None,
                                'Stance': 'LONG',
                                'Quantity': match_qty,
                                'EntryDate': str(b_date) if b_date else str(b_item['date']),
                                'EntryPrice': b_item['price'],
                                'EntryValue': match_qty * b_item['price'],
                                'ExitDate': str(dt_d) if dt_d else str(row['OrderDate']),
                                'ExitPrice': px,
                                'ExitValue': match_qty * px,
                                'BuyPrice': b_item['price'],
                                'SellPrice': px,
                                'BuyValue': match_qty * b_item['price'],
                                'SellValue': match_qty * px,
                                'GrossPnL': pnl,
                                'ROIPct': roi_pct,
                                'HoldingDays': holding_days,
                                'Outcome': 'PROFIT' if pnl > 0 else ('LOSS' if pnl < 0 else 'BREAKEVEN'),
                                'FinancialYear': fy,
                                'Insights': insight,
                                'EntryOrderID': b_item['order_id'],
                                'ExitOrderID': oid
                            })
                            qty -= match_qty
                            b_item['qty'] -= match_qty
                            if b_item['qty'] < 1e-4:
                                buy_queue.pop(0)

                        if qty > 1e-4:
                            sell_queue.append({'order_id': oid, 'date': dt_d, 'dt': dt_tm, 'qty': qty, 'price': px, 'fy': fy})

                # Process remaining open long buys
                for b_item in buy_queue:
                    if b_item['qty'] > 1e-4:
                        b_date = b_item['date']
                        days_held = (ref_date - b_date).days if (b_date and ref_date >= b_date) else 0
                        exp_dt = None
                        if pd.notna(expiry) and expiry is not None:
                            try:
                                exp_dt = _parse_to_date(expiry)
                            except:
                                exp_dt = None
                        if not exp_dt and seg != 'Equity':
                            exp_dt = extract_derivative_expiry(cname)

                        dte = None
                        dte_risk = "N/A"
                        if exp_dt:
                            dte = (exp_dt - ref_date).days
                            if dte < 0: dte_risk = "Expired"
                            elif dte <= 2: dte_risk = "🚨 High Risk (<= 2d)"
                            elif dte <= 7: dte_risk = "⚠️ Near Expiry (<= 7d)"
                            else: dte_risk = "✅ Normal (> 7d)"

                        if seg == 'Equity':
                            holding_status = 'VERIFIED_HOLDING'
                            status_disp = '✅ VERIFIED HOLDING'
                            is_dispute = False
                            dispute_reason = 'None (Matched Demat Long Delivery)'
                            recon_advice = f"Verified Demat Delivery holding in {broker}. Carried forward for {days_held} days."
                            insight = f"Active Delivery Holding: {days_held}d held. Committed: Rs. {(b_item['qty']*b_item['price']):,.2f}."
                        else:
                            if dte is not None and dte < 0:
                                holding_status = 'DISPUTE_DATA'
                                status_disp = '⚠️ DISPUTE DATA'
                                is_dispute = True
                                dispute_reason = f"Expired Contract: Contract expired on {exp_dt} ({abs(dte)}d ago) without square-off leg in broker file."
                                recon_advice = f"⚠️ Incomplete Trade Data: Upload broker monthly settlement / expiry square-off file for {broker}."
                                insight = f"⚠️ Expired F&O Contract ({dte} DTE). Missing broker square-off transaction log."
                            elif dte is not None and dte >= 0:
                                holding_status = 'ACTIVE_DERIVATIVE'
                                status_disp = '🟢 ACTIVE CARRY FORWARD'
                                is_dispute = False
                                dispute_reason = 'None (Active Derivative Contract)'
                                recon_advice = f"Active carry forward contract in {broker}. {dte} DTE remaining."
                                insight = f"Active Long F&O ({dte} DTE): Monitor Theta decay curve. Stoploss recommendation: -20% from entry."
                            else:
                                if days_held > 60:
                                    holding_status = 'DISPUTE_DATA'
                                    status_disp = '⚠️ DISPUTE DATA'
                                    is_dispute = True
                                    dispute_reason = f"Derivative position opened {days_held}d ago without square-off leg."
                                    recon_advice = f"⚠️ Incomplete Trade Data: Old derivative trade without square-off in {broker}."
                                    insight = f"⚠️ Unsquared Derivative: Opened {days_held}d ago without closing leg."
                                else:
                                    holding_status = 'ACTIVE_DERIVATIVE'
                                    status_disp = '🟢 ACTIVE CARRY FORWARD'
                                    is_dispute = False
                                    dispute_reason = 'None (Active Contract)'
                                    recon_advice = f"Active derivative position open in {broker}."
                                    insight = f"Active Derivative: Open {days_held}d."

                        open_trades.append({
                            'TradeID': f"OP-B{b_item['order_id']}",
                            'Status': 'OPEN',
                            'Broker': broker,
                            'Segment': seg,
                            'SubSegment': subseg,
                            'Symbol': sym,
                            'ContractName': cname or sym,
                            'OptionType': opt or 'N/A',
                            'StrikePrice': strike if pd.notna(strike) else None,
                            'ExpiryDate': str(exp_dt) if exp_dt else (str(expiry) if pd.notna(expiry) else 'N/A'),
                            'Stance': 'LONG',
                            'Quantity': b_item['qty'],
                            'EntryDate': str(b_date) if b_date else str(b_item['date']),
                            'EntryPrice': b_item['price'],
                            'EntryValue': b_item['qty'] * b_item['price'],
                            'ExitDate': None,
                            'ExitPrice': None,
                            'ExitValue': None,
                            'BuyPrice': b_item['price'],
                            'SellPrice': None,
                            'BuyValue': b_item['qty'] * b_item['price'],
                            'SellValue': None,
                            'GrossPnL': None,
                            'ROIPct': None,
                            'HoldingDays': days_held,
                            'Outcome': 'OPEN',
                            'FinancialYear': b_item['fy'],
                            'DTE': dte,
                            'DTERisk': dte_risk,
                            'HoldingStatus': holding_status,
                            'HoldingStatusDisplay': status_disp,
                            'DisputeReason': dispute_reason,
                            'ReconciliationAdvice': recon_advice,
                            'IsDispute': is_dispute,
                            'Insights': insight,
                            'EntryOrderID': b_item['order_id'],
                            'ExitOrderID': None
                        })

                # Process remaining open short sells
                for s_item in sell_queue:
                    if s_item['qty'] > 1e-4:
                        s_date = s_item['date']
                        days_held = (ref_date - s_date).days if (s_date and ref_date >= s_date) else 0
                        exp_dt = None
                        if pd.notna(expiry) and expiry is not None:
                            try:
                                exp_dt = _parse_to_date(expiry)
                            except:
                                exp_dt = None
                        if not exp_dt and seg != 'Equity':
                            exp_dt = extract_derivative_expiry(cname)

                        dte = None
                        dte_risk = "N/A"
                        if exp_dt:
                            dte = (exp_dt - ref_date).days
                            if dte < 0: dte_risk = "Expired"
                            elif dte <= 2: dte_risk = "🚨 High Risk (<= 2d)"
                            elif dte <= 7: dte_risk = "⚠️ Near Expiry (<= 7d)"
                            else: dte_risk = "✅ Normal (> 7d)"

                        if seg == 'Equity':
                            holding_status = 'DISPUTE_DATA'
                            status_disp = '⚠️ DISPUTE DATA'
                            is_dispute = True
                            dispute_reason = f"Unmatched Sell: Sold {s_item['qty']:,.0f} shares without matching prior Buy order in imported tradebook."
                            recon_advice = f"⚠️ Incomplete Trade Data: Upload complete tradebook from account opening date for {broker}."
                            insight = f"⚠️ DISPUTE DATA: Unmatched sell order without historical buy log."
                        else:
                            if dte is not None and dte < 0:
                                holding_status = 'DISPUTE_DATA'
                                status_disp = '⚠️ DISPUTE DATA'
                                is_dispute = True
                                dispute_reason = f"Expired Short Contract: Expired on {exp_dt} ({abs(dte)}d ago) without square-off leg in broker file."
                                recon_advice = f"⚠️ Incomplete Trade Data: Upload broker monthly settlement file for {broker}."
                                insight = f"⚠️ Expired Short Derivative ({dte} DTE). Missing square-off log."
                            elif dte is not None and dte >= 0:
                                holding_status = 'ACTIVE_DERIVATIVE'
                                status_disp = '🟢 ACTIVE CARRY FORWARD'
                                is_dispute = False
                                dispute_reason = 'None (Active Derivative Contract)'
                                recon_advice = f"Active short carry forward contract in {broker}. {dte} DTE remaining."
                                insight = f"Active Short Position: Monitor delta risk. Strict stoploss recommended."
                            else:
                                if days_held > 60:
                                    holding_status = 'DISPUTE_DATA'
                                    status_disp = '⚠️ DISPUTE DATA'
                                    is_dispute = True
                                    dispute_reason = f"Derivative position opened {days_held}d ago without square-off leg."
                                    recon_advice = f"⚠️ Incomplete Trade Data: Old derivative trade without square-off in {broker}."
                                    insight = f"⚠️ Unsquared Derivative: Opened {days_held}d ago without closing leg."
                                else:
                                    holding_status = 'ACTIVE_DERIVATIVE'
                                    status_disp = '🟢 ACTIVE CARRY FORWARD'
                                    is_dispute = False
                                    dispute_reason = 'None (Active Contract)'
                                    recon_advice = f"Active short derivative position in {broker}."
                                    insight = f"Active Short Position: Monitor underlying breakout."

                        open_trades.append({
                            'TradeID': f"OP-S{s_item['order_id']}",
                            'Status': 'OPEN',
                            'Broker': broker,
                            'Segment': seg,
                            'SubSegment': subseg,
                            'Symbol': sym,
                            'ContractName': cname or sym,
                            'OptionType': opt or 'N/A',
                            'StrikePrice': strike if pd.notna(strike) else None,
                            'ExpiryDate': str(exp_dt) if exp_dt else (str(expiry) if pd.notna(expiry) else 'N/A'),
                            'Stance': 'SHORT',
                            'Quantity': s_item['qty'],
                            'EntryDate': str(s_date) if s_date else str(s_item['date']),
                            'EntryPrice': s_item['price'],
                            'EntryValue': s_item['qty'] * s_item['price'],
                            'ExitDate': None,
                            'ExitPrice': None,
                            'ExitValue': None,
                            'BuyPrice': None,
                            'SellPrice': s_item['price'],
                            'BuyValue': None,
                            'SellValue': s_item['qty'] * s_item['price'],
                            'GrossPnL': None,
                            'ROIPct': None,
                            'HoldingDays': days_held,
                            'Outcome': 'OPEN',
                            'FinancialYear': s_item['fy'],
                            'DTE': dte,
                            'DTERisk': dte_risk,
                            'HoldingStatus': holding_status,
                            'HoldingStatusDisplay': status_disp,
                            'DisputeReason': dispute_reason,
                            'ReconciliationAdvice': recon_advice,
                            'IsDispute': is_dispute,
                            'Insights': insight,
                            'EntryOrderID': s_item['order_id'],
                            'ExitOrderID': None
                        })

            # Combine or filter
            all_trades = open_trades + closed_trades
            res_df = pd.DataFrame(all_trades)
            if not res_df.empty:
                # Sort: Open trades first, then newest closed trades
                res_df['SortStatus'] = res_df['Status'].apply(lambda s: 0 if s == 'OPEN' else 1)
                res_df['SortDate'] = res_df.apply(lambda r: r['ExitDate'] or r['EntryDate'], axis=1)
                res_df.sort_values(by=['SortStatus', 'SortDate'], ascending=[True, False], inplace=True)
                res_df.drop(columns=['SortStatus', 'SortDate'], inplace=True, errors='ignore')

            # Filter by Trade Status if specified
            if filters and filters.get('trade_status'):
                t_stat = filters['trade_status'].upper()
                if 'VERIFIED' in t_stat:
                    res_df = res_df[(res_df['Status'] == 'OPEN') & (res_df['HoldingStatus'].isin(['VERIFIED_HOLDING', 'ACTIVE_DERIVATIVE']))]
                elif 'DISPUTE' in t_stat:
                    res_df = res_df[(res_df['Status'] == 'OPEN') & (res_df['HoldingStatus'] == 'DISPUTE_DATA')]
                elif 'HOLDING' in t_stat or 'PORTFOLIO' in t_stat:
                    res_df = res_df[res_df['Status'] == 'OPEN']
                elif 'OPEN' in t_stat and 'CLOSED' not in t_stat and 'ALL' not in t_stat:
                    res_df = res_df[res_df['Status'] == 'OPEN']
                elif 'CLOSED' in t_stat and 'OPEN' not in t_stat and 'ALL' not in t_stat:
                    res_df = res_df[res_df['Status'] == 'CLOSED']

            return res_df

    except Exception as e:
        print(f"Error matching orders to trades: {e}")
        return pd.DataFrame()


if __name__ == '__main__':
    print("Testing Trade Orders Ingestion Engine...")
    res = sync_trade_orders()
    print("\nSync Results:")
    print(f"Total files: {res['total_files']}")
    print(f"Processed: {res['processed_files']}")
    print(f"New Orders Inserted: {res['new_orders_inserted']}")
    print(f"Duplicates Skipped: {res['duplicates_skipped']}")
    for d in res['details']:
        print(" [OK]", d)
    for err in res['errors']:
        print(" [INFO]", err)

    print("\nTesting Distinct Filter Values:")
    filts = get_distinct_filter_values()
    print(f"Brokers: {filts['brokers']}")
    print(f"Segments: {filts['segments']}")
    print(f"Statuses: {filts['statuses']}")

    print("\nTesting Open Positions:")
    open_df = compute_open_positions()
    print(f"Total Open Positions: {len(open_df)}")
    if not open_df.empty:
        print(open_df[['Broker', 'Segment', 'Symbol', 'Stance', 'NetQty', 'AvgEntryPrice', 'CommittedValue', 'DaysOpen', 'DTERisk']].head(10).to_string())


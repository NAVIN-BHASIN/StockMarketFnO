import os
import re
import shutil
import sys
import pandas as pd
from datetime import datetime

# Add workspace directory to path
sys.path.append(r"C:\users\navin\StockMarketFnO")
from db_utils import DatabaseHelper

db = DatabaseHelper()

# Source Directories
PARTICIPANT_DIR = r"D:\FnOImport\Participants wise Data"
FII_STATS_DIR = r"D:\FnOImport\FII Derivatives Statistics"

col_mapping = {
    'Future Index Long': ('Future Index', 'Long'),
    'Future Index Short': ('Future Index', 'Short'),
    'Future Stock Long': ('Future Stock', 'Long'),
    'Future Stock Short': ('Future Stock', 'Short'),
    'Option Index Call Long': ('Option Index Call', 'Long'),
    'Option Index Call Short': ('Option Index Call', 'Short'),
    'Option Index Put Long': ('Option Index Put', 'Long'),
    'Option Index Put Short': ('Option Index Put', 'Short'),
    'Option Stock Call Long': ('Option Stock Call', 'Long'),
    'Option Stock Call Short': ('Option Stock Call', 'Short'),
    'Option Stock Put Long': ('Option Stock Put', 'Long'),
    'Option Stock Put Short': ('Option Stock Put', 'Short'),
}

def clean_val(val):
    if pd.isna(val) or val == '' or str(val).strip() == '-':
        return None
    try:
        return int(float(str(val).replace(',', '').strip()))
    except:
        return None

def get_backup_dir(base_dir):
    backup_path = os.path.join(base_dir, 'Backup')
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    return backup_path

def find_participant_files():
    paths = [PARTICIPANT_DIR, FII_STATS_DIR]
    files_by_date = {} # date_str -> {'OI': (file_path, base_dir), 'VOL': (file_path, base_dir)}
    
    for base_dir in paths:
        if not os.path.exists(base_dir):
            continue
        for file in os.listdir(base_dir):
            file_path = os.path.join(base_dir, file)
            if os.path.isdir(file_path):
                continue
                
            match_oi = re.match(r'fao_participant_oi_(\d{8})\.csv', file, re.IGNORECASE)
            match_vol = re.match(r'fao_participant_vol_(\d{8})\.csv', file, re.IGNORECASE)
            
            if match_oi:
                date_raw = match_oi.group(1)
                date_str = f"{date_raw[4:8]}-{date_raw[2:4]}-{date_raw[0:2]}"
                if date_str not in files_by_date:
                    files_by_date[date_str] = {'OI': None, 'VOL': None}
                files_by_date[date_str]['OI'] = (file_path, base_dir)
                
            elif match_vol:
                date_raw = match_vol.group(1)
                date_str = f"{date_raw[4:8]}-{date_raw[2:4]}-{date_raw[0:2]}"
                if date_str not in files_by_date:
                    files_by_date[date_str] = {'OI': None, 'VOL': None}
                files_by_date[date_str]['VOL'] = (file_path, base_dir)
                
    return files_by_date

def parse_participant_files(oi_path, vol_path, date_str):
    pos_dict = {}
    
    def process_file(file_path, field_type):
        df = pd.read_csv(file_path, header=1)
        df.columns = df.columns.str.strip()
        
        for idx, row in df.iterrows():
            client_type = str(row['Client Type']).strip()
            if not client_type or client_type == 'Client Type':
                continue
                
            for col, (inst_type, side) in col_mapping.items():
                if col in row:
                    val = clean_val(row[col])
                    key = (client_type, inst_type)
                    if key not in pos_dict:
                        pos_dict[key] = {
                            'SnapshotDate': date_str,
                            'ClientType': client_type,
                            'InstrumentType': inst_type,
                            'OI_Long': None, 'OI_Short': None,
                            'Vol_Long': None, 'Vol_Short': None
                        }
                    
                    if field_type == 'OI':
                        if side == 'Long':
                            pos_dict[key]['OI_Long'] = val
                        else:
                            pos_dict[key]['OI_Short'] = val
                    elif field_type == 'VOL':
                        if side == 'Long':
                            pos_dict[key]['Vol_Long'] = val
                        else:
                            pos_dict[key]['Vol_Short'] = val

    if oi_path and os.path.exists(oi_path):
        process_file(oi_path, 'OI')
    if vol_path and os.path.exists(vol_path):
        process_file(vol_path, 'VOL')
        
    return list(pos_dict.values())

def import_positions_to_db(data_list):
    if not data_list:
        return
        
    rows = []
    for d in data_list:
        rows.append((
            d['SnapshotDate'],
            d['ClientType'],
            d['InstrumentType'],
            None if d['OI_Long'] is None or pd.isna(d['OI_Long']) else int(d['OI_Long']),
            None if d['OI_Short'] is None or pd.isna(d['OI_Short']) else int(d['OI_Short']),
            None if d['Vol_Long'] is None or pd.isna(d['Vol_Long']) else int(d['Vol_Long']),
            None if d['Vol_Short'] is None or pd.isna(d['Vol_Short']) else int(d['Vol_Short'])
        ))
        
    placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?)"] * len(rows))
    query = f"""
    DECLARE @p dbo.ut_ParticipantPositions;
    INSERT INTO @p (SnapshotDate, ClientType, InstrumentType, OI_Long, OI_Short, Vol_Long, Vol_Short)
    VALUES {placeholders};
    EXEC dbo.sp_ImportParticipantPositions @p;
    """
    
    flat_params = [val for row in rows for val in row]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, flat_params)
        conn.commit()

def find_fii_stats_files():
    paths = [FII_STATS_DIR, PARTICIPANT_DIR]
    fii_files = []
    
    for base_dir in paths:
        if not os.path.exists(base_dir):
            continue
        for file in os.listdir(base_dir):
            file_path = os.path.join(base_dir, file)
            if os.path.isdir(file_path):
                continue
                
            match = re.match(r'fii_stats_(\d{1,2}-[a-zA-Z]{3}-\d{4})\.(xls|csv)', file, re.IGNORECASE)
            if match:
                date_raw = match.group(1)
                try:
                    dt = datetime.strptime(date_raw, '%d-%b-%Y')
                    date_str = dt.strftime('%Y-%m-%d')
                    fii_files.append((file_path, date_str, base_dir))
                except Exception as e:
                    print(f"Error parsing date from FII Stats filename {file}: {e}")
                    
    return fii_files

def parse_fii_stats(file_path, date_str):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        df = pd.read_csv(file_path, header=None, encoding='utf-8')
    else:
        df = pd.read_excel(file_path, header=None)
        
    products = [
        "INDEX FUTURES", "BANKNIFTY FUTURES", "FINNIFTY FUTURES", "MIDCPNIFTY FUTURES", 
        "NIFTY FUTURES", "NIFTYNXT50 FUTURES", "INDEX OPTIONS", "BANKNIFTY OPTIONS", 
        "FINNIFTY OPTIONS", "MIDCPNIFTY OPTIONS", "NIFTY OPTIONS", "NIFTYNXT50 OPTIONS",
        "STOCK FUTURES", "STOCK OPTIONS"
    ]
    
    parsed_rows = []
    for idx, row in df.iterrows():
        prod_name = str(row[0]).strip().upper()
        if prod_name in products:
            buy_contracts = int(clean_val(row[1])) if clean_val(row[1]) is not None else None
            buy_value = clean_val(row[2])
            sell_contracts = int(clean_val(row[3])) if clean_val(row[3]) is not None else None
            sell_value = clean_val(row[4])
            oi_contracts = int(clean_val(row[5])) if clean_val(row[5]) is not None else None
            oi_value = clean_val(row[6])
            
            parsed_rows.append((
                date_str,
                prod_name,
                buy_contracts,
                buy_value,
                sell_contracts,
                sell_value,
                oi_contracts,
                oi_value
            ))
            
    return parsed_rows

def import_fii_stats_to_db(rows):
    if not rows:
        return
        
    placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?)"] * len(rows))
    query = f"""
    DECLARE @p dbo.ut_FIIDerivativesStats;
    INSERT INTO @p (SnapshotDate, Product, Buy_Contracts, Buy_Value_Cr, Sell_Contracts, Sell_Value_Cr, OI_Contracts, OI_Value_Cr)
    VALUES {placeholders};
    EXEC dbo.sp_ImportFIIDerivativesStats @p;
    """
    
    flat_params = [val for row in rows for val in row]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, flat_params)
        conn.commit()

def move_to_backup(file_path, base_dir):
    try:
        backup_dir = get_backup_dir(base_dir)
        dest_path = os.path.join(backup_dir, os.path.basename(file_path))
        
        # If destination already exists, delete it first to avoid collision
        if os.path.exists(dest_path):
            os.remove(dest_path)
            
        shutil.move(file_path, backup_dir)
        print(f"Moved {os.path.basename(file_path)} to Backup.")
    except Exception as e:
        print(f"Failed to backup file {os.path.basename(file_path)}: {e}")

def run_import():
    print("--- Starting FnO Data Ingestion Job ---")
    
    # 1. Process Participant wise Data
    participant_files = find_participant_files()
    print(f"Found participant files for {len(participant_files)} dates.")
    
    for date_str, files in participant_files.items():
        oi_info = files['OI']
        vol_info = files['VOL']
        
        oi_path = oi_info[0] if oi_info else None
        vol_path = vol_info[0] if vol_info else None
        
        print(f"Processing Participant positions for {date_str}...")
        try:
            data = parse_participant_files(oi_path, vol_path, date_str)
            if data:
                import_positions_to_db(data)
                
                # Backup successfully processed files
                if oi_info:
                    move_to_backup(oi_info[0], oi_info[1])
                if vol_info:
                    move_to_backup(vol_info[0], vol_info[1])
        except Exception as e:
            print(f"Error processing participant data for {date_str}: {e}")
            
    # 2. Process FII Stats
    fii_stats_files = find_fii_stats_files()
    print(f"Found {len(fii_stats_files)} FII Stats files.")
    
    for file_path, date_str, base_dir in fii_stats_files:
        print(f"Processing FII Stats for {date_str} ({os.path.basename(file_path)})...")
        try:
            rows = parse_fii_stats(file_path, date_str)
            if rows:
                import_fii_stats_to_db(rows)
                move_to_backup(file_path, base_dir)
        except Exception as e:
            print(f"Error processing FII stats file {os.path.basename(file_path)}: {e}")
            
    print("--- Ingestion Job Completed ---")

if __name__ == '__main__':
    run_import()

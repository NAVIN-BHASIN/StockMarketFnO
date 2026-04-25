new_method = '''
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

'''
with open('db_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()
marker = '    def get_lot_size(self, symbol):'
if 'get_symbols_by_filters' not in content:
    content = content.replace(marker, new_method + marker, 1)
    with open('db_utils.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched successfully')
else:
    print('Already patched')

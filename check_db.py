from db_utils import DatabaseHelper
import pandas as pd
import sys

db = DatabaseHelper()
try:
    with db.get_connection() as conn:
        tables = pd.read_sql("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'", conn)
        print("Tables in Database:")
        print(tables['TABLE_NAME'].tolist())
except Exception as e:
    print("Error:", e)

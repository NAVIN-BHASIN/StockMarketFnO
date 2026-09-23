from db_utils import DatabaseHelper
db = DatabaseHelper()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
    for row in cursor.fetchall():
        print(f"{row[0]}.{row[1]}")

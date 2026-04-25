import pyodbc

def create_database():
    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\\SQLEXPRESS;DATABASE=master;Trusted_Connection=yes;'
    try:
        conn = pyodbc.connect(connection_string, autocommit=True)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT name FROM sys.databases WHERE name = 'StockMarket'")
        if not cursor.fetchone():
            print("Creating database 'StockMarket'...")
            cursor.execute("CREATE DATABASE StockMarket")
        else:
            print("Database 'StockMarket' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error creating database (Make sure SQL Server Express is running and accessible): {e}")

def create_tables():
    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\\SQLEXPRESS;DATABASE=StockMarket;Trusted_Connection=yes;'
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Instruments Table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Instruments' AND xtype='U')
            CREATE TABLE Instruments (
                InstrumentID INT IDENTITY(1,1) PRIMARY KEY,
                Symbol VARCHAR(50) NOT NULL,
                InstrumentType VARCHAR(20) NOT NULL, -- 'FUT', 'OPT', 'EQ'
                Sector VARCHAR(50),
                ExpiryDate DATE
            )
        ''')
        
        # Daily Prices Table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DailyPrices' AND xtype='U')
            CREATE TABLE DailyPrices (
                PriceID INT IDENTITY(1,1) PRIMARY KEY,
                InstrumentID INT FOREIGN KEY REFERENCES Instruments(InstrumentID),
                Date DATE NOT NULL,
                OpenPrice DECIMAL(18,2),
                HighPrice DECIMAL(18,2),
                LowPrice DECIMAL(18,2),
                ClosePrice DECIMAL(18,2),
                Volume INT,
                OpenInterest INT
            )
        ''')
        
        # Insert some dummy data if empty
        cursor.execute("SELECT COUNT(*) FROM Instruments")
        if cursor.fetchone()[0] == 0:
            print("Inserting dummy data...")
            cursor.execute("INSERT INTO Instruments (Symbol, InstrumentType, Sector, ExpiryDate) VALUES ('RELIANCE', 'FUT', 'Energy', '2026-05-30')")
            cursor.execute("INSERT INTO Instruments (Symbol, InstrumentType, Sector, ExpiryDate) VALUES ('HDFCBANK', 'FUT', 'Banking', '2026-05-30')")
            cursor.execute("INSERT INTO Instruments (Symbol, InstrumentType, Sector, ExpiryDate) VALUES ('TCS', 'FUT', 'IT', '2026-05-30')")
            
            # Dummy prices
            cursor.execute('''
                INSERT INTO DailyPrices (InstrumentID, Date, OpenPrice, HighPrice, LowPrice, ClosePrice, Volume, OpenInterest)
                VALUES 
                (1, '2026-04-18', 2900, 2950, 2890, 2940, 10000, 50000),
                (1, '2026-04-19', 2940, 2980, 2920, 2975, 12000, 52000),
                (1, '2026-04-20', 2975, 3010, 2950, 3000, 15000, 55000),
                (2, '2026-04-20', 1500, 1520, 1490, 1515, 20000, 80000),
                (3, '2026-04-20', 3800, 3850, 3780, 3820, 8000, 30000)
            ''')
            
        conn.commit()
        print("Tables and data setup complete.")
        conn.close()
    except Exception as e:
        print(f"Error setting up tables: {e}")

if __name__ == '__main__':
    create_database()
    create_tables()

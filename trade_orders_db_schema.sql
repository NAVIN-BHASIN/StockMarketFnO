IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'TradeOrders_Master')
BEGIN
    CREATE TABLE TradeOrders_Master (
        OrderID BIGINT IDENTITY(1,1) PRIMARY KEY,
        OrderHash VARCHAR(64) UNIQUE NOT NULL,
        Broker VARCHAR(50) NOT NULL,
        Exchange VARCHAR(20) NULL,
        Segment VARCHAR(30) NOT NULL,
        SubSegment VARCHAR(50) NULL,
        Symbol VARCHAR(50) NOT NULL,
        ContractName VARCHAR(150) NULL,
        ISIN VARCHAR(30) NULL,
        OptionType VARCHAR(10) NULL,
        StrikePrice FLOAT NULL,
        ExpiryDate DATE NULL,
        OrderDateTime DATETIME NOT NULL,
        OrderDate DATE NOT NULL,
        OrderTime VARCHAR(15) NULL,
        Action VARCHAR(10) NOT NULL,
        OrderType VARCHAR(30) NULL,
        Product VARCHAR(30) NULL,
        OrderQty FLOAT NOT NULL,
        ExecutedQty FLOAT NOT NULL,
        OrderPrice FLOAT NULL,
        ExecutionPrice FLOAT NULL,
        TriggerPrice FLOAT NULL,
        OrderStatus VARCHAR(30) NOT NULL,
        RejectionReason VARCHAR(250) NULL,
        BrokerOrderNo VARCHAR(80) NULL,
        ExchangeOrderNo VARCHAR(80) NULL,
        FinancialYear VARCHAR(20) NOT NULL,
        CalYear INT NOT NULL,
        CalMonth INT NOT NULL,
        SourceFile VARCHAR(250) NOT NULL,
        CreatedAt DATETIME DEFAULT GETDATE()
    );
    CREATE INDEX IX_TradeOrders_Date ON TradeOrders_Master(OrderDate);
    CREATE INDEX IX_TradeOrders_Symbol ON TradeOrders_Master(Symbol);
    CREATE INDEX IX_TradeOrders_Broker ON TradeOrders_Master(Broker);
    CREATE INDEX IX_TradeOrders_Status ON TradeOrders_Master(OrderStatus);
    PRINT 'TradeOrders_Master table created successfully.';
END
ELSE
BEGIN
    PRINT 'TradeOrders_Master table already exists.';
END

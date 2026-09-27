-- Schema for Institutional Multi-Broker Trading Journal
USE [Navin_Personal];

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TradingJournal_Master' AND xtype='U')
BEGIN
    CREATE TABLE TradingJournal_Master (
        TradeID BIGINT IDENTITY(1,1) PRIMARY KEY,
        TradeHash VARCHAR(64) NOT NULL UNIQUE,
        Broker VARCHAR(50) NOT NULL,
        Segment VARCHAR(30) NOT NULL,
        SubSegment VARCHAR(30),
        Symbol VARCHAR(100) NOT NULL,
        ContractName VARCHAR(255),
        ISIN VARCHAR(30),
        Sector VARCHAR(100),
        OptionType VARCHAR(10),
        StrikePrice FLOAT,
        ExpiryDate DATE,
        TradeType VARCHAR(20) DEFAULT 'LONG',
        EntryDate DATE NOT NULL,
        ExitDate DATE NOT NULL,
        Quantity FLOAT NOT NULL,
        BuyPrice FLOAT,
        BuyValue FLOAT,
        SellPrice FLOAT,
        SellValue FLOAT,
        HoldingDays INT,
        GrossPnL FLOAT NOT NULL,
        Brokerage FLOAT DEFAULT 0.0,
        STT FLOAT DEFAULT 0.0,
        ExchangeCharges FLOAT DEFAULT 0.0,
        GST FLOAT DEFAULT 0.0,
        StampDuty FLOAT DEFAULT 0.0,
        OtherCharges FLOAT DEFAULT 0.0,
        TotalCharges FLOAT DEFAULT 0.0,
        NetPnL FLOAT NOT NULL,
        ROIPct FLOAT,
        IsMTF BIT DEFAULT 0,
        MTFFundedAmount FLOAT DEFAULT 0.0,
        MTFMarginAmount FLOAT DEFAULT 0.0,
        MTFInterestCost FLOAT DEFAULT 0.0,
        MTFNetReturn FLOAT DEFAULT 0.0,
        FinancialYear VARCHAR(15) NOT NULL,
        CalYear INT NOT NULL,
        CalMonth INT NOT NULL,
        Outcome VARCHAR(15),
        MistakeTag VARCHAR(100),
        SetupTag VARCHAR(100),
        Notes NVARCHAR(MAX),
        Rating INT DEFAULT 0,
        SourceFile VARCHAR(255),
        SourceSheet VARCHAR(100),
        CreatedAt DATETIME DEFAULT GETDATE(),
        LastUpdatedAt DATETIME DEFAULT GETDATE()
    );

    CREATE NONCLUSTERED INDEX IX_TJM_FY_Segment ON TradingJournal_Master (FinancialYear, Segment, Broker);
    CREATE NONCLUSTERED INDEX IX_TJM_ExitDate ON TradingJournal_Master (ExitDate DESC);
    CREATE NONCLUSTERED INDEX IX_TJM_Symbol ON TradingJournal_Master (Symbol);
    CREATE NONCLUSTERED INDEX IX_TJM_TradeHash ON TradingJournal_Master (TradeHash);
    PRINT 'TradingJournal_Master created successfully.';
END
ELSE
BEGIN
    PRINT 'TradingJournal_Master already exists.';
END;

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TradingJournal_OtherLedger' AND xtype='U')
BEGIN
    CREATE TABLE TradingJournal_OtherLedger (
        LedgerID BIGINT IDENTITY(1,1) PRIMARY KEY,
        LedgerHash VARCHAR(64) NOT NULL UNIQUE,
        Broker VARCHAR(50) NOT NULL,
        PostingDate DATE NOT NULL,
        Particulars VARCHAR(500) NOT NULL,
        Category VARCHAR(50),
        Debit FLOAT DEFAULT 0.0,
        Credit FLOAT DEFAULT 0.0,
        FinancialYear VARCHAR(15) NOT NULL,
        SourceFile VARCHAR(255),
        CreatedAt DATETIME DEFAULT GETDATE()
    );

    CREATE NONCLUSTERED INDEX IX_TJOL_Broker_Date ON TradingJournal_OtherLedger (Broker, PostingDate);
    CREATE NONCLUSTERED INDEX IX_TJOL_LedgerHash ON TradingJournal_OtherLedger (LedgerHash);
    PRINT 'TradingJournal_OtherLedger created successfully.';
END
ELSE
BEGIN
    PRINT 'TradingJournal_OtherLedger already exists.';
END;

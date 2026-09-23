-- =========================================================================
-- NSE Participant Positions & FII Derivatives Statistics Database Setup
-- Description: Creates required tables, User-Defined Table Types (UDTTs),
--              and Stored Procedures (SPs) to handle daily data imports.
-- Author: Antigravity AI
-- Date: 2026-08-15
-- =========================================================================

-- 1. Create Table: NSE_Participant_Positions
IF OBJECT_ID('dbo.NSE_Participant_Positions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.NSE_Participant_Positions (
        SnapshotDate DATE NOT NULL,
        ClientType VARCHAR(20) NOT NULL,
        InstrumentType VARCHAR(50) NOT NULL,
        OI_Long BIGINT NULL,
        OI_Short BIGINT NULL,
        Vol_Long BIGINT NULL,
        Vol_Short BIGINT NULL,
        CreatedDate DATETIME DEFAULT GETDATE(),
        CONSTRAINT PK_NSE_Participant_Positions PRIMARY KEY CLUSTERED (SnapshotDate, ClientType, InstrumentType)
    );
    PRINT 'Table [dbo.NSE_Participant_Positions] created successfully.';
END
ELSE
BEGIN
    PRINT 'Table [dbo.NSE_Participant_Positions] already exists.';
END
GO

-- 2. Create Table: NSE_FII_Derivatives_Stats
IF OBJECT_ID('dbo.NSE_FII_Derivatives_Stats', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.NSE_FII_Derivatives_Stats (
        SnapshotDate DATE NOT NULL,
        Product VARCHAR(50) NOT NULL,
        Buy_Contracts BIGINT NULL,
        Buy_Value_Cr DECIMAL(18, 2) NULL,
        Sell_Contracts BIGINT NULL,
        Sell_Value_Cr DECIMAL(18, 2) NULL,
        OI_Contracts BIGINT NULL,
        OI_Value_Cr DECIMAL(18, 2) NULL,
        CreatedDate DATETIME DEFAULT GETDATE(),
        CONSTRAINT PK_NSE_FII_Derivatives_Stats PRIMARY KEY CLUSTERED (SnapshotDate, Product)
    );
    PRINT 'Table [dbo.NSE_FII_Derivatives_Stats] created successfully.';
END
ELSE
BEGIN
    PRINT 'Table [dbo.NSE_FII_Derivatives_Stats] already exists.';
END
GO

-- 3. Create User-Defined Table Type for Participant Positions
IF TYPE_ID('dbo.ut_ParticipantPositions') IS NULL
BEGIN
    CREATE TYPE dbo.ut_ParticipantPositions AS TABLE (
        SnapshotDate DATE,
        ClientType VARCHAR(20),
        InstrumentType VARCHAR(50),
        OI_Long BIGINT,
        OI_Short BIGINT,
        Vol_Long BIGINT,
        Vol_Short BIGINT
    );
    PRINT 'User-Defined Table Type [dbo.ut_ParticipantPositions] created.';
END
ELSE
BEGIN
    PRINT 'User-Defined Table Type [dbo.ut_ParticipantPositions] already exists.';
END
GO

-- 4. Create User-Defined Table Type for FII Derivatives Stats
IF TYPE_ID('dbo.ut_FIIDerivativesStats') IS NULL
BEGIN
    CREATE TYPE dbo.ut_FIIDerivativesStats AS TABLE (
        SnapshotDate DATE,
        Product VARCHAR(50),
        Buy_Contracts BIGINT,
        Buy_Value_Cr DECIMAL(18, 2),
        Sell_Contracts BIGINT,
        Sell_Value_Cr DECIMAL(18, 2),
        OI_Contracts BIGINT,
        OI_Value_Cr DECIMAL(18, 2)
    );
    PRINT 'User-Defined Table Type [dbo.ut_FIIDerivativesStats] created.';
END
ELSE
BEGIN
    PRINT 'User-Defined Table Type [dbo.ut_FIIDerivativesStats] already exists.';
END
GO

-- 5. Stored Procedure to Import/Upsert Participant Positions
CREATE OR ALTER PROCEDURE dbo.sp_ImportParticipantPositions
    @Positions dbo.ut_ParticipantPositions READONLY
AS
BEGIN
    SET NOCOUNT ON;
    
    MERGE dbo.NSE_Participant_Positions AS Target
    USING @Positions AS Source
    ON (Target.SnapshotDate = Source.SnapshotDate 
        AND Target.ClientType = Source.ClientType 
        AND Target.InstrumentType = Source.InstrumentType)
    WHEN MATCHED THEN
        UPDATE SET 
            Target.OI_Long = Source.OI_Long,
            Target.OI_Short = Source.OI_Short,
            Target.Vol_Long = Source.Vol_Long,
            Target.Vol_Short = Source.Vol_Short,
            Target.CreatedDate = GETDATE()
    WHEN NOT MATCHED THEN
        INSERT (SnapshotDate, ClientType, InstrumentType, OI_Long, OI_Short, Vol_Long, Vol_Short)
        VALUES (Source.SnapshotDate, Source.ClientType, Source.InstrumentType, Source.OI_Long, Source.OI_Short, Source.Vol_Long, Source.Vol_Short);
        
    PRINT 'Participant positions upserted successfully.';
END
GO

-- 6. Stored Procedure to Import/Upsert FII Derivatives Stats
CREATE OR ALTER PROCEDURE dbo.sp_ImportFIIDerivativesStats
    @Stats dbo.ut_FIIDerivativesStats READONLY
AS
BEGIN
    SET NOCOUNT ON;
    
    MERGE dbo.NSE_FII_Derivatives_Stats AS Target
    USING @Stats AS Source
    ON (Target.SnapshotDate = Source.SnapshotDate 
        AND Target.Product = Source.Product)
    WHEN MATCHED THEN
        UPDATE SET 
            Target.Buy_Contracts = Source.Buy_Contracts,
            Target.Buy_Value_Cr = Source.Buy_Value_Cr,
            Target.Sell_Contracts = Source.Sell_Contracts,
            Target.Sell_Value_Cr = Source.Sell_Value_Cr,
            Target.OI_Contracts = Source.OI_Contracts,
            Target.OI_Value_Cr = Source.OI_Value_Cr,
            Target.CreatedDate = GETDATE()
    WHEN NOT MATCHED THEN
        INSERT (SnapshotDate, Product, Buy_Contracts, Buy_Value_Cr, Sell_Contracts, Sell_Value_Cr, OI_Contracts, OI_Value_Cr)
        VALUES (Source.SnapshotDate, Source.Product, Source.Buy_Contracts, Source.Buy_Value_Cr, Source.Sell_Contracts, Source.Sell_Value_Cr, Source.OI_Contracts, Source.OI_Value_Cr);
        
    PRINT 'FII Derivatives statistics upserted successfully.';
END
GO

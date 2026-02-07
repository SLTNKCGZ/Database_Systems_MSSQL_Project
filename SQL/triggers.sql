--Triggers
 --1
CREATE TRIGGER trg_OfferLine_Management
ON OfferLine
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT * FROM inserted)
    BEGIN
        UPDATE OL
        SET OL.PurchaseTotalPrice = i.Quantity * PI.PurchaseUnitPrice,
            OL.LineItemProfitability = CASE WHEN i.SalesUnitPrice = 0 THEN 0 
                                            ELSE (i.SalesUnitPrice - PI.PurchaseUnitPrice) / i.SalesUnitPrice END
        FROM OfferLine OL
        INNER JOIN inserted i ON OL.OfferNo = i.OfferNo AND OL.ProductCode = i.ProductCode
        INNER JOIN ProductInventory PI ON i.ProductCode = PI.ProductCode;
    END

    DECLARE @AffectedOffers TABLE (OfferNo INT);
    INSERT INTO @AffectedOffers SELECT OfferNo FROM inserted UNION SELECT OfferNo FROM deleted;

    UPDATE O
    SET O.SalesAmountUSD = ISNULL(Agg.TotalSales, 0),
        O.PurchaseAmountUSD = ISNULL(Agg.TotalPurchase, 0),
        O.ProfitUSD = ISNULL(Agg.TotalSales, 0) - ISNULL(Agg.TotalPurchase, 0),
        O.ProfitPercent = CASE WHEN ISNULL(Agg.TotalSales, 0) = 0 THEN 0 
                               ELSE ((ISNULL(Agg.TotalSales, 0) - ISNULL(Agg.TotalPurchase, 0)) / Agg.TotalSales) * 100 END
    FROM Offer O
    INNER JOIN (
        SELECT OfferNo, SUM(SalesTotalPrice) AS TotalSales, SUM(ISNULL(PurchaseTotalPrice, 0)) AS TotalPurchase
        FROM OfferLine WHERE OfferNo IN (SELECT OfferNo FROM @AffectedOffers)
        GROUP BY OfferNo
    ) AS Agg ON O.OfferNo = Agg.OfferNo;
END;
GO
--test
SELECT * FROM Offer
INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice) 
VALUES (101, 'PROD001', 5, 120.00);

SELECT * FROM Offer WHERE OfferNo = 1;
--2
CREATE TRIGGER trg_Order_PostInsert_Process
ON [Order]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE O
    SET O.SalesAmountUSD = [Off].SalesAmountUSD,
        O.PurchaseAmountUSD = [Off].PurchaseAmountUSD,
        O.ProfitTL = ([Off].SalesAmountUSD - [Off].PurchaseAmountUSD) * i.DailyUSDExchangeRate
    FROM [Order] O
    INNER JOIN inserted i ON O.SaleID = i.SaleID
    INNER JOIN Offer [Off] ON i.OfferNo = [Off].OfferNo;

    UPDATE PI
    SET PI.ReservedStock = PI.ReservedStock - OL.Quantity,
        PI.FieldStock = PI.FieldStock + OL.Quantity
    FROM ProductInventory PI
    INNER JOIN OfferLine OL ON PI.ProductCode = OL.ProductCode
    INNER JOIN inserted i ON OL.OfferNo = i.OfferNo;

    DECLARE @OfferNo INT, @CUserID INT, @ProdCode VARCHAR(50), @Qty INT;
    SELECT TOP 1 @OfferNo = i.OfferNo, @CUserID = [Off].CUserID FROM inserted i INNER JOIN Offer [Off] ON i.OfferNo = [Off].OfferNo;

    DECLARE line_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT ProductCode, Quantity FROM OfferLine WHERE OfferNo = @OfferNo;
    OPEN line_cursor;
    FETCH NEXT FROM line_cursor INTO @ProdCode, @Qty;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        UPDATE Product SET CUserID = @CUserID WHERE SerialNumber IN (
            SELECT TOP (@Qty) SerialNumber FROM (
                SELECT S.StorageSerialNumber AS SerialNumber, S.SProductCode AS PC FROM Storage S
                UNION ALL SELECT Se.ServerSerialNumber, Se.SeProductCode FROM [Server] Se
            ) AS Combined WHERE PC = @ProdCode AND SerialNumber NOT IN (SELECT SerialNumber FROM Product WHERE CUserID IS NOT NULL)
            ORDER BY NEWID()
        );
        FETCH NEXT FROM line_cursor INTO @ProdCode, @Qty;
    END;
    CLOSE line_cursor; DEALLOCATE line_cursor;
END;
GO
SELECT * FROM Product
--test
INSERT INTO [dbo].[Order] (
    [PaymentType],         
    [DailyUSDExchangeRate], -- Decimal(18,4)
    [OfferNo],              
    [SEUserID],            
    [SaleDate]           
) 
VALUES (
    'CreditCard',           
    34.2550,                
    1,                    
    26,                    
    GETDATE()               
);
SELECT * FROM [dbo].[Order] 
SELECT * FROM ProductInventory
CREATE TRIGGER trg_RepairRequest_Handle
ON RepairRequest
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- IsRepair Bayraðýný ve Stoklarý Tek Seferde Güncelle
    UPDATE P SET P.IsRepair = 1 FROM Product P INNER JOIN inserted i ON P.SerialNumber = i.SerialNumber;

    UPDATE PI
    SET PI.FieldStock = PI.FieldStock - 1, PI.UnderRepairStock = PI.UnderRepairStock + 1
    FROM ProductInventory PI
    INNER JOIN (
        SELECT COALESCE(S.SProductCode, Se.SeProductCode) AS PCode, P.SerialNumber
        FROM Product P
        LEFT JOIN Storage S ON P.SerialNumber = S.StorageSerialNumber
        LEFT JOIN [Server] Se ON P.SerialNumber = Se.ServerSerialNumber
        INNER JOIN inserted i ON P.SerialNumber = i.SerialNumber
    ) AS Prod ON PI.ProductCode = Prod.PCode;
END;
GO
----test

--INSERT INTO ServerInventory (SeProductCode, CPU, RAM, Disk)
--VALUES ('SRV-100', 8, 32, '1TB SSD');
---- 1. Ürün Kodunu Envantere ekle
--INSERT INTO ProductInventory (ProductCode, ProductDescription, PurchaseUnitPrice, FieldStock, ProductType)
--VALUES ('SRV-100', 'Test Sunucusu', 5000.00, 10, 'Server');

---- 2. Sunucu detayýný ekle (PCode eþleþmesi için)
--INSERT INTO [Server] (ServerSerialNumber, IPAddress, Service, SeProductCode)
--VALUES ('SN-TEST-999', '192.168.1.1', 'Database', 'SRV-100');

---- 3. Ürünü oluþtur
--INSERT INTO Product (SerialNumber, Name, MacAddress, FirmwareVersion, IsRepair)
--VALUES ('SN-TEST-999', 'Test Prod', 'AA:BB:CC:DD', 'v1.0', 0);

--INSERT INTO RepairRequest (SerialNumber, Date, Status)
--VALUES ('SN-TEST-999', GETDATE(), 'NotAccepted');

---- KONTROL 1: Ürünün IsRepair bayraðý 1 oldu mu?
--SELECT SerialNumber, IsRepair FROM Product WHERE SerialNumber = 'SN-TEST-999';

---- KONTROL 2: Stoklar kaydýrýldý mý? 
---- (FieldStock: 9, UnderRepairStock: 1 olmalý)
--SELECT ProductCode, FieldStock, UnderRepairStock 
--FROM ProductInventory WHERE ProductCode = 'SRV-100';

CREATE TRIGGER trg_Repair_Finalize
ON Repair
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT UPDATE(Response) RETURN;

    -- Sadece 'COMPLETED' durumuna geçen kayýtlarý iþle
    UPDATE R SET R.EndDate = GETDATE() FROM Repair R INNER JOIN inserted i ON R.RepairID = i.RepairID WHERE i.Response = 'COMPLETED';

    UPDATE RR SET RR.Status = 'COMPLETED' FROM RepairRequest RR INNER JOIN inserted i ON RR.RequestID = i.RequestID WHERE i.Response = 'COMPLETED';

    UPDATE P SET P.IsRepair = 0 FROM Product P INNER JOIN RepairRequest RR ON P.SerialNumber = RR.SerialNumber INNER JOIN inserted i ON RR.RequestID = i.RequestID WHERE i.Response = 'COMPLETED';

    -- Stoklarý UnderRepair -> Field yap
    UPDATE PI SET PI.UnderRepairStock = PI.UnderRepairStock - 1, PI.FieldStock = PI.FieldStock + 1
    FROM ProductInventory PI
    INNER JOIN (
        SELECT COALESCE(S.SProductCode, Se.SeProductCode) AS PCode FROM Product P
        LEFT JOIN Storage S ON P.SerialNumber = S.StorageSerialNumber
        LEFT JOIN [Server] Se ON P.SerialNumber = Se.ServerSerialNumber
        INNER JOIN RepairRequest RR ON P.SerialNumber = RR.SerialNumber
        INNER JOIN inserted i ON RR.RequestID = i.RequestID WHERE i.Response = 'COMPLETED'
    ) AS Prod ON PI.ProductCode = Prod.PCode;
END;
GO

----test
---- Eðer Repair tablosunda kayýt yoksa (RequestID'yi RepairRequest tablosundan bulun)
--DECLARE @ReqID INT = (SELECT TOP 1 RequestID FROM RepairRequest WHERE SerialNumber = 'SN-TEST-999' ORDER BY Date DESC);
---- Teknisyen ID'si olarak sistemde var olan bir Technician ID kullanmalýsýnýz (Örn: 26)
--INSERT INTO Repair (RequestID, StartDate, Response, TEUserID)
--VALUES (@ReqID, GETDATE(), 'NOT COMPLETED', 51);

--SELECT EUserID, HourlySalary FROM dbo.Technician;
---- En son eklenen tamir kaydýný 'COMPLETED' yapalým
--UPDATE Repair 
--SET Response = 'COMPLETED' 
--WHERE RequestID = (SELECT TOP 1 RequestID FROM RepairRequest WHERE SerialNumber = 'SN-TEST-999' ORDER BY Date DESC);


CREATE TRIGGER trg_Server_AddStock
ON [Server]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Eklenen Server cihazlarýný say ve Inventory'i güncelle
    UPDATE PI
    SET PI.AvailableStock = PI.AvailableStock + Agg.ItemCount
    FROM ProductInventory PI
    INNER JOIN (
        SELECT SeProductCode, COUNT(*) as ItemCount
        FROM inserted
        GROUP BY SeProductCode
    ) AS Agg ON PI.ProductCode = Agg.SeProductCode;
END;
GO

CREATE TRIGGER trg_Storage_AddStock
ON Storage
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Eklenen Storage cihazlarýný say ve Inventory'i güncelle
    UPDATE PI
    SET PI.AvailableStock = PI.AvailableStock + Agg.ItemCount
    FROM ProductInventory PI
    INNER JOIN (
        SELECT SProductCode, COUNT(*) as ItemCount
        FROM inserted
        GROUP BY SProductCode
    ) AS Agg ON PI.ProductCode = Agg.SProductCode;
END;
GO
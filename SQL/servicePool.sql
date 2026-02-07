USE ServicePool;

CREATE TABLE [Address] (
    AddressID INT PRIMARY KEY IDENTITY(1,1),
    Country NVARCHAR(20) NOT NULL,
    City NVARCHAR(20) NOT NULL,
    PostalCode INT NOT NULL,
    FullAddress NVARCHAR(200),
    AddressType NVARCHAR(20),
);

CREATE TABLE [User] (
    UserID INT PRIMARY KEY IDENTITY(1,1), 
    Password NVARCHAR(50) NOT NULL,
    RegisterDate DATETIME DEFAULT GETDATE(),
    UserType NVARCHAR(20) NOT NULL,
    AddressID INT,
    CONSTRAINT FK_Address FOREIGN KEY (AddressID) REFERENCES [Address](AddressID),
);


CREATE TABLE [Employee] (
    EUserID INT PRIMARY KEY, 
    TC VARCHAR(11) UNIQUE NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    MiddleName NVARCHAR(50),
    LastName NVARCHAR(50) NOT NULL,
    BirthDate DATE NOT NULL,
    HiredDate DATE NOT NULL,
    Age AS (DATEDIFF(YEAR, BirthDate, GETDATE())),
    EmployeeType NVARCHAR(15) NOT NULL
);


CREATE TABLE [E-MailAdress] (
    EUserID INT,
    MailAddress NVARCHAR(100),
    PRIMARY KEY (EUserID, MailAddress) -- Composite PK
);

CREATE TABLE [E-TelNo] (
    EUserID INT,
    TelCode CHAR(3),
    TelNo VARCHAR(20),
    PRIMARY KEY (EUserID, TelCode, TelNo) -- Composite PK
);

CREATE TABLE CustomerCompany (
    CUserID INT PRIMARY KEY,
    TradeRegistryNumber VARCHAR(50) UNIQUE NOT NULL,
    CompanyTradeName NVARCHAR(100) NOT NULL,
    Website NVARCHAR(100),
    YearOfEstablishment INT,
    TaxOffice NVARCHAR(50) NOT NULL,
    TaxNumber VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE CommunityCompany (
    MailAddress NVARCHAR(100) NOT NULL,
    CUserID INT,
    DepartmentName NVARCHAR(50) NOT NULL,
    TelCode VARCHAR(10) NOT NULL,
    TelNo VARCHAR(20) UNIQUE NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    MiddleName NVARCHAR(50),  
    LastName NVARCHAR(50) NOT NULL,
    PRIMARY KEY (MailAddress, CUserID)
);
 
CREATE TABLE SalariedEmployee (
    EUserID INT PRIMARY KEY, 
    Salary DECIMAL(18, 2),
    MEUserID INT, 
    DepartmentNo INT, --bu da foreign key ama department ile karþýlýklý foreign keyleri olduðu için altta tanýmlandý.  
);



CREATE TABLE Technician (
    EUserID INT PRIMARY KEY, 
    HourlySalary DECIMAL(18, 2) NOT NULL
);

CREATE TABLE Department (
    DepartmentNo INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(100) NOT NULL,
    MngrSUserID INT NOT NULL,
    CONSTRAINT FK_Department_Manager FOREIGN KEY (MngrSUserID) REFERENCES [SalariedEmployee](EUserID)
);

CREATE TABLE ProductInventory (
    ProductCode VARCHAR(50) PRIMARY KEY,
    ProductDescription NVARCHAR(255) NOT NULL,
    PurchaseUnitPrice DECIMAL(18, 2) NOT NULL,
    AvailableStock INT DEFAULT 0,  --ilk kez product oluþturulduðunda eðer deðer girilmezse 0 olarak alýrýz ilk baþta her þeyi
    ReservedStock INT DEFAULT 0,
    FieldStock INT DEFAULT 0,     -- Satýlmýþ ve sahada (müþteride) olanlar
    UnderRepairStock INT DEFAULT 0,
    TotalStock AS (AvailableStock + ReservedStock),
    ProductType NVARCHAR(50) NOT NULL  --Storage, server ya da diðerleri olabilir
);

CREATE TABLE StorageInventory (
    SProductCode VARCHAR(50) PRIMARY KEY, 
    DiskType NVARCHAR(50) NOT NULL, --SSD, SAS
    DiskSpace NVARCHAR(50) NOT NULL, --2TiB
    DiskCount INT -- 12, 10
);

CREATE TABLE ServerInventory (
    SeProductCode VARCHAR(50) PRIMARY KEY, 
    CPU INT NOT NULL, --3, 5
    RAM INT NOT NULL, --16, 8
    Disk NVARCHAR(50) NOT NULL --200GB, 1TB
);

CREATE TABLE Product (
    SerialNumber VARCHAR(50) PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    MacAddress VARCHAR(50) UNIQUE NOT NULL,
    FirmwareVersion VARCHAR(50) NOT NULL,
    IsRepair BIT DEFAULT 0, -- True/False
    CUserID INT, --FK
    CONSTRAINT FK_Product_Customer FOREIGN KEY (CUserID) REFERENCES [CustomerCompany](CUserID)
);

CREATE TABLE Storage (
    StorageSerialNumber VARCHAR(50) PRIMARY KEY, 
    ManagementIPAddress1 VARCHAR(20) NOT NULL,
    ManagementIPAddress2 VARCHAR(20) NOT NULL,
    ServiceIPAddress1 VARCHAR(20) NOT NULL,
    ServiceIPAddress2 VARCHAR(20) NOT NULL,
    LUN NVARCHAR(50) NOT NULL,
    Capacity INT NOT NULL, --LUN kapasitesi diyor ama lun storagee özel bu da storage tablosunda yer alabilir bence.
    SProductCode VARCHAR(50) NOT NULL, --FK
    CONSTRAINT FK_Storage_Inv FOREIGN KEY (SProductCode) REFERENCES [StorageInventory](SProductCode)
);

CREATE TABLE StorageWWN (
    StorageSerialNumber VARCHAR(50) UNIQUE,
    WWN VARCHAR(100),
    PRIMARY KEY (StorageSerialNumber, WWN)
);

CREATE TABLE [Server] (
    ServerSerialNumber VARCHAR(50) PRIMARY KEY, 
    IPAddress VARCHAR(20) NOT NULL,
    OperatingSystem NVARCHAR(100),
    Service NVARCHAR(100) NOT NULL,
    SeProductCode VARCHAR(50) NOT NULL,
    CONSTRAINT FK_Server_Inv FOREIGN KEY (SeProductCode) REFERENCES [ServerInventory](SeProductCode)
);



CREATE TABLE Offer (
    OfferNo INT PRIMARY KEY IDENTITY(1,1),
    Date DATETIME DEFAULT GETDATE(),
    SalesAmountUSD DECIMAL(18, 2), --procedure + trigger offerlinelerdan sonra sales total priceler toplanarak hesaplanacak.
   SalesAmountTL AS (ExchangeRate * SalesAmountUSD),
    PurchaseAmountUSD DECIMAL(18, 2), --offerlineler belirlendikten sonra deðiþecek. her offerline eklendiðinde deðiþmeli.
    ExchangeRate DECIMAL(18, 4) NOT NULL,
    Status NVARCHAR(20) DEFAULT 'NotAccepted',  --iki seçenek olarak düþündük. Baþka da olabilir.
    PaymentTerm DATE NOT NULL,  --ödeme vadesi date + vade eklenerek bulunur. procedure ile belirlenebilir.
    Term NVARCHAR(50) NOT NULL, --vade girilir.

    ProfitUSD DECIMAL(18,2), --AS (SalesAmountUSD - PurchaseAmountUSD),
    ProfitTL  DECIMAL(18,2),--AS ((SalesAmountUSD - PurchaseAmountUSD) * ExchangeRate),
    ProfitPercent  DECIMAL(18,2),--AS (
        --CASE 
            --WHEN SalesAmountTL = 0 THEN 0
            --ELSE (( (SalesAmountUSD - PurchaseAmountUSD) * ExchangeRate ) / SalesAmountTL) * 100
        --END
    --), -- Sales amount tl gibi sonradan belirlenecek þeyler olduðu için bunlarýn da prodeculer ya da triggerlerla belirlenmesi gerekebilir. 

    CUserID INT NOT NULL, --FK
    CONSTRAINT FK_Offer_Customer FOREIGN KEY (CUserID) REFERENCES CustomerCompany(CUserID)
);


CREATE TABLE OfferLine (
    OfferNo INT,
    ProductCode VARCHAR(50),
    Quantity INT NOT NULL,
    SalesUnitPrice DECIMAL(18, 2) NOT NULL,
    SalesTotalPrice AS (Quantity * SalesUnitPrice),
    PurchaseTotalPrice DECIMAL(18,2),
    LineItemProfitability DECIMAL(2,1), --Procedure
    PRIMARY KEY (OfferNo, ProductCode)
);

CREATE TABLE [Order] (
    SaleID INT PRIMARY KEY IDENTITY(1,1),
    PaymentType NVARCHAR(50) NOT NULL,
    DailyUSDExchangeRate DECIMAL(18, 4) NOT NULL,
    SaleDate DATE DEFAULT GETDATE(),
    SalesAmountUSD DECIMAL(18, 2),
    PurchaseAmountUSD DECIMAL(18, 2),
    SEUserID INT, 
    OfferNo INT,

    ProfitTL DECIMAL(12,5),--store procedure + trigger(after insert), sales amount tl ve purchase amount usd günlük kura göre hesaplanýr

    CONSTRAINT FK_SaleOrder_Employee FOREIGN KEY (SEUserID) REFERENCES SalariedEmployee(EUserID),
    CONSTRAINT FK_SaleOrder_Offer FOREIGN KEY (OfferNo) REFERENCES Offer(OfferNo)
);



CREATE TABLE CustomerFeedBack (
    FeedbackID INT PRIMARY KEY IDENTITY(1,1),
    SaleID INT,
    CUserID INT,
    Rating INT NOT NULL,
    FeedbackText NVARCHAR(MAX),
    Date DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Feedback_Sale FOREIGN KEY (SaleID) REFERENCES [Order](SaleID),
    CONSTRAINT FK_Feedback_Customer FOREIGN KEY (CUserID) REFERENCES [CustomerCompany](CUserID)
);

CREATE TABLE RepairRequest (
    RequestID INT PRIMARY KEY IDENTITY(1,1),
    Status NVARCHAR(50) DEFAULT 'NOT COMPLETED',  --SONRADAN DEÐÝÞECEK. update
    Date DATETIME DEFAULT GETDATE(),
    SerialNumber VARCHAR(50),
    CONSTRAINT FK_RepairReq_Product FOREIGN KEY (SerialNumber) REFERENCES [Product](SerialNumber)
);

CREATE TABLE Repair (
    RepairID INT PRIMARY KEY IDENTITY(1,1),
    RequestID INT,
    StartDate DATETIME DEFAULT GETDATE(),
    EndDate DATETIME,  --GÜNCELLENECEK SONRADAN trigger
    Response NVARCHAR(20) DEFAULT 'NOT COMPLETED',  --Response complete olduðunda enddate güncellenebilir --store procedure + trigger
    TEUserID INT,
    CONSTRAINT FK_Repair_Request FOREIGN KEY (RequestID) REFERENCES [RepairRequest](RequestID),
    CONSTRAINT FK_Repair_Tech FOREIGN KEY (TEUserID) REFERENCES [Technician](EUserID)
);

ALTER TABLE [SalariedEmployee] 
ADD CONSTRAINT FK_Salaried_Dept FOREIGN KEY (DepartmentNo) REFERENCES [Department](DepartmentNo);
--CHECK CONSTRAINTS
-- Address
ALTER TABLE [Address]
ADD CONSTRAINT CK_Address_PostalCode CHECK (PostalCode >= 0);

-- CustomerCompany
ALTER TABLE CustomerCompany
ADD CONSTRAINT CK_YearOfEstablishment CHECK (YearOfEstablishment >= 0);

-- SalariedEmployee
ALTER TABLE SalariedEmployee
ADD CONSTRAINT CK_Salary_Positive CHECK (Salary > 0);

-- Technician
ALTER TABLE Technician
ADD CONSTRAINT CK_HourlySalary_Positive CHECK (HourlySalary > 0);

-- ProductInventory
ALTER TABLE ProductInventory
ADD CONSTRAINT CK_PurchaseUnitPrice_Positive CHECK (PurchaseUnitPrice > 0);

-- StorageInventory
ALTER TABLE StorageInventory
ADD CONSTRAINT CK_DiskCount_Positive CHECK (DiskCount >= 0);

-- ServerInventory
ALTER TABLE ServerInventory
ADD CONSTRAINT CK_CPU_Positive CHECK (CPU > 0),
    CONSTRAINT CK_RAM_Positive CHECK (RAM > 0);

-- Storage
ALTER TABLE Storage
ADD CONSTRAINT CK_Capacity_Positive CHECK (Capacity > 0);

-- Offer
ALTER TABLE Offer
ADD CONSTRAINT CK_SalesAmountUSD_Positive CHECK (SalesAmountUSD >= 0),
    CONSTRAINT CK_PurchaseAmountUSD_Positive CHECK (PurchaseAmountUSD >= 0),
    CONSTRAINT CK_ExchangeRate_Positive CHECK (ExchangeRate > 0);

-- OfferLine
ALTER TABLE OfferLine
ADD CONSTRAINT CK_Quantity_Positive CHECK (Quantity > 0),
    CONSTRAINT CK_SalesUnitPrice_Positive CHECK (SalesUnitPrice > 0);

-- Order
ALTER TABLE [Order]
ADD CONSTRAINT CK_DailyUSDExchangeRate_Positive CHECK (DailyUSDExchangeRate > 0);


ALTER TABLE [E-TelNo]
ADD CONSTRAINT CK_TelCode_Format CHECK (TelCode LIKE '+%');

ALTER TABLE CommunityCompany
ADD CONSTRAINT CK_Community_TelCode_Format CHECK (TelCode LIKE '+%');


-- Offer Status
ALTER TABLE Offer
ADD CONSTRAINT CK_Offer_Status
CHECK (Status IN ('NotAccepted', 'Accepted', 'Rejected'));

-- RepairRequest Status
ALTER TABLE RepairRequest
ADD CONSTRAINT CK_RepairRequest_Status
CHECK (Status IN ('NotAccepted', 'Accepted', 'Rejected'));

-- Repair Response
ALTER TABLE Repair
ADD CONSTRAINT CK_Repair_Response
CHECK (Response IN ('NOT COMPLETED', 'COMPLETED'));

-- UserType
ALTER TABLE [User]
ADD CONSTRAINT CK_User_Type
CHECK (UserType IN ('Employee', 'CustomerCompany'));


-- DiskType
ALTER TABLE StorageInventory
ADD CONSTRAINT CK_Disk_Type
CHECK (DiskType IN ('SSD', 'SAS', 'HDD'));

-- PaymentType
ALTER TABLE [Order]
ADD CONSTRAINT CK_Payment_Type
CHECK (PaymentType IN ('Cash', 'CreditCard', 'Transfer'));



ALTER TABLE CustomerFeedBack
ADD CONSTRAINT CK_Rating_Range CHECK (Rating BETWEEN 1 AND 5);



--INDEXES
CREATE NONCLUSTERED INDEX IX_CustomerCompany_Name 
ON CustomerCompany(CompanyTradeName);

CREATE NONCLUSTERED INDEX IX_Product_MacAddress 
ON Product(MacAddress);

CREATE NONCLUSTERED INDEX IX_Order_Date 
ON [Order](SaleDate);

-- Clustered ? UserID
-- Nonclustered
CREATE NONCLUSTERED INDEX IX_User_UserType
ON [User](UserType);



CREATE NONCLUSTERED INDEX IX_Employee_EUserID
ON Employee(EUserID);

-- PK clustered (DepartmentNo)

CREATE NONCLUSTERED INDEX IX_Department_Manager
ON Department(MngrSUserID);

-- PK clustered (EUserID)

CREATE NONCLUSTERED INDEX IX_SalariedEmployee_Department
ON SalariedEmployee(DepartmentNo);

CREATE NONCLUSTERED INDEX IX_SalariedEmployee_Manager
ON SalariedEmployee(MEUserID);


-- PK clustered (ProductCode)

CREATE NONCLUSTERED INDEX IX_ProductInventory_Type
ON ProductInventory(ProductType);


CREATE NONCLUSTERED INDEX IX_Product_CUserID
ON Product(CUserID);


-- PK clustered (StorageSerialNumber)

CREATE NONCLUSTERED INDEX IX_Storage_ProductCode
ON Storage(SProductCode);


CREATE NONCLUSTERED INDEX IX_Offer_CUserID
ON Offer(CUserID);

CREATE NONCLUSTERED INDEX IX_Offer_Status
ON Offer(Status);

-- PK clustered (OfferNo, ProductCode)

CREATE NONCLUSTERED INDEX IX_OfferLine_ProductCode
ON OfferLine(ProductCode);

CREATE NONCLUSTERED INDEX IX_Order_OfferNo
ON [Order](OfferNo);

CREATE NONCLUSTERED INDEX IX_Order_SEUserID
ON [Order](SEUserID);

CREATE NONCLUSTERED INDEX CX_Feedback_SaleID
ON CustomerFeedBack(SaleID);

CREATE NONCLUSTERED INDEX IX_Feedback_CUserID
ON CustomerFeedBack(CUserID);


CREATE NONCLUSTERED INDEX IX_RepairRequest_Status
ON RepairRequest(Status);

CREATE NONCLUSTERED INDEX IX_Repair_Technician
ON Repair(TEUserID);


CREATE PROCEDURE sp_AuthenticateEmployee
@TC VARCHAR(11) 
AS
BEGIN
    SELECT e.EUserID, e.TC, e.FirstName, e.middleName, e.LastName, u.UserID, u.Password, u.UserType
    FROM Employee e
    INNER JOIN [User] u ON e.EUserID = u.UserID
    WHERE e.TC = @TC
END
GO
CREATE PROCEDURE sp_AuthenticateCustomer
@RegistryNo NVARCHAR(50) 
AS
BEGIN
    SELECT c.CUserID, c.TradeRegistryNumber, c.CompanyTradeName, u.UserID, u.Password, u.UserType
           FROM CustomerCompany c
           INNER JOIN [User] u ON c.CUserID = u.UserID
           WHERE c.TradeRegistryNumber = @RegistryNo
END
GO
CREATE PROCEDURE sp_RegisterSalariedEmployee
    @Password NVARCHAR(50),
    @TC VARCHAR(11),
    @FirstName NVARCHAR(50),
    @MiddleName NVARCHAR(50) = NULL, -- Opsiyonel
    @LastName NVARCHAR(50),
    @BirthDate DATE,
    @HiredDate DATE,
    @DepartmentName NVARCHAR(100) = NULL -- Departman ismi gelecek, ID'yi biz bulacaðýz
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Hata yönetimi için Transaction baþlatýyoruz
    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @NewUserID INT;
        DECLARE @DepartmentNo INT;

        -- 1. [User] tablosuna ekleme
        INSERT INTO [User] (Password, RegisterDate, UserType)
        VALUES (@Password, GETDATE(), 'Employee');

        -- Yeni oluþan UserID'yi al
        SET @NewUserID = SCOPE_IDENTITY();

        -- 2. Employee tablosuna ekleme
        INSERT INTO Employee (EUserID, TC, FirstName, MiddleName, LastName, BirthDate, HiredDate, EmployeeType)
        VALUES (@NewUserID, @TC, @FirstName, @MiddleName, @LastName, @BirthDate, @HiredDate, 'Salaried');

        -- 3. Departman isminden ID bulma (Eðer isim geldiyse)
        IF @DepartmentName IS NOT NULL
        BEGIN
            SELECT @DepartmentNo = DepartmentNo 
            FROM Department 
            WHERE Name = @DepartmentName;
        END

        -- 4. SalariedEmployee tablosuna ekleme (Salary ve MEUserID þimdilik NULL)
        INSERT INTO SalariedEmployee (EUserID, Salary, MEUserID, DepartmentNo)
        VALUES (@NewUserID, NULL, NULL, @DepartmentNo);

        -- Her þey yolunda giderse iþlemi onayla
        COMMIT TRANSACTION;
        
        -- Geriye oluþturulan ID'yi döndür (Ýstersen Python tarafýnda kullanmak için)
        SELECT @NewUserID AS NewUserID;
    END TRY
    BEGIN CATCH
        -- Hata olursa tüm iþlemleri geri al
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        
        -- Hatayý fýrlat
        THROW;
    END CATCH
END;
GO
CREATE PROCEDURE sp_RegisterCustomerCompany
    @Password NVARCHAR(50),
    @TradeRegistryNumber VARCHAR(50),
    @CompanyTradeName NVARCHAR(100),
    @Website NVARCHAR(100) = NULL,      
    @YearOfEstablishment INT = NULL,    
    @TaxOffice NVARCHAR(50),
    @TaxNumber VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @NewUserID INT;

        -- 1. [User] tablosuna ekleme (UserType = 'CustomerCompany')
        INSERT INTO [User] (Password, RegisterDate, UserType)
        VALUES (@Password, GETDATE(), 'CustomerCompany');

        -- Yeni oluþan UserID'yi al
        SET @NewUserID = SCOPE_IDENTITY();

        -- 2. CustomerCompany tablosuna ekleme
        INSERT INTO CustomerCompany (
            CUserID, 
            TradeRegistryNumber, 
            CompanyTradeName, 
            Website, 
            YearOfEstablishment, 
            TaxOffice, 
            TaxNumber
        )
        VALUES (
            @NewUserID, 
            @TradeRegistryNumber, 
            @CompanyTradeName, 
            @Website, 
            @YearOfEstablishment, 
            @TaxOffice, 
            @TaxNumber
        );

        -- Ýþlemi onayla
        COMMIT TRANSACTION;
        
        -- Oluþan ID'yi geri döndür
        SELECT @NewUserID AS NewCustomerID;
    END TRY
    BEGIN CATCH
        -- Hata olursa geri al
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;




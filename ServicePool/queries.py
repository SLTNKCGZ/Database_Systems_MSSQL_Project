"""
SQL Queries Repository
Tüm SQL sorguları bu dosyada merkezi olarak tutulur.
"""

# ============================================================================
# CUSTOMER QUERIES
# ============================================================================

CUSTOMER = {
    # Customer ID bulma
    "get_customer_id": """
        SELECT CUserID FROM CustomerCompany WHERE CUserID = :user_id
    """,
    
    # Customer CompanyTradeName bulma
    "get_customer_name": """
        SELECT CompanyTradeName FROM CustomerCompany WHERE CUserID = :customer_id
    """,
    
    # Customer Offers (tarih filtresi ile)
    "get_customer_offers": """
        SELECT 
            v.OfferNo,
            v.OfferDate,
            v.Status,
            v.SalesAmountTL AS TotalAmount,
            v.Customer
        FROM vw_OfferSummary v
        WHERE v.Customer = :customer_name
        {date_filter}
        ORDER BY v.OfferDate DESC
    """,
    
    # Offer detayları
    "get_offer_details": """
        SELECT 
            os.OfferNo, 
            os.OfferDate, 
            os.Status, 
            os.SalesAmountTL AS TotalAmount,
            os.Customer
        FROM vw_OfferSummary os
        WHERE os.OfferNo = :offer_id AND os.Customer = :customer_name
    """,
    
    # Offer bilgileri (accept için)
    "get_offer_for_accept": """
        SELECT OfferNo, CUserID, Date AS OfferDate, Status, SalesAmountTL AS TotalAmount, ExchangeRate
        FROM Offer
        WHERE OfferNo = :offer_id AND CUserID = :customer_id
    """,
    
    # Offer'ı kabul et (Procedure kullanarak)
    "accept_offer": """
        EXEC sp_AcceptOffer 
            @OfferNo = :offer_no,
            @PaymentType = :payment_type,
            @DailyUSDExchangeRate = :exchange_rate
    """,
    
    # OfferLine detayları
    "get_offer_line_details": """
        SELECT 
            old.OfferNo,
            old.ProductCode,
            old.Quantity,
            old.SalesUnitPrice AS UnitPrice,
            old.SalesTotalPrice AS TotalPrice,
            old.ProductDescription AS Description,
            old.ProductDescription AS ProductName
        FROM vw_OfferLineDetails old
        WHERE old.OfferNo = :offer_id
    """,
    
    # Customer Orders (tarih filtresi ile)
    "get_customer_orders": """
        SELECT
            v.SaleID AS OrderID,
            v.SaleDate,
            v.SalesAmountUSD AS TotalAmount,
            v.Customer,
            COALESCE(v.status, 'NotCompleted') AS Status
        FROM vw_OrderSummary v
        WHERE v.Customer = :customer_name
        {date_filter}
        ORDER BY v.SaleDate DESC
    """,
    
    # Order detayları
    "get_order_details": """
        SELECT 
            os.SaleID AS OrderID, 
            os.OfferNo,
            os.SaleDate, 
            os.SalesAmountUSD AS TotalAmount, 
            os.Customer,
            COALESCE(os.status, 'NotCompleted') AS Status
        FROM vw_OrderSummary os
        WHERE os.SaleID = :order_id AND os.Customer = :customer_name
    """,
    
    # Order'ın OfferNo'sunu al
    "get_order_offer_no": """
        SELECT OfferNo FROM vw_OrderSummary WHERE SaleID = :order_id AND Customer = :customer_name
    """,
    
    # OrderLine detayları (SerialNumber ile)
    "get_order_line_details": """
        SELECT 
            old.OfferNo,
            old.ProductCode,
            old.Quantity,
            old.SalesUnitPrice AS UnitPrice,
            old.SalesTotalPrice AS TotalPrice,
            old.ProductDescription AS Description,
            old.ProductDescription AS ProductName,
            (SELECT TOP 1 P.SerialNumber 
             FROM Product P
             WHERE P.CUserID = :customer_id
               AND (
                   EXISTS (SELECT 1 FROM [Server] S WHERE S.ServerSerialNumber = P.SerialNumber AND S.SeProductCode = old.ProductCode)
                   OR EXISTS (SELECT 1 FROM Storage St WHERE St.StorageSerialNumber = P.SerialNumber AND St.SProductCode = old.ProductCode)
               )
             ORDER BY P.SerialNumber) AS SerialNumber
        FROM vw_OfferLineDetails old
        WHERE old.OfferNo = :offer_no
    """,
    
    # Customer Products (detaylı)
    "get_customer_products": """
        SELECT 
            p.SerialNumber,
            p.Name AS ProductName,
            p.MacAddress,
            p.FirmwareVersion,
            p.IsRepair,
            COALESCE(s.SeProductCode, st.SProductCode) AS ProductCode,
            CASE 
                WHEN s.ServerSerialNumber IS NOT NULL THEN 'Server'
                WHEN st.StorageSerialNumber IS NOT NULL THEN 'Storage'
                ELSE 'Other'
            END AS ProductType,
            s.IPAddress AS ServerIP,
            s.OperatingSystem,
            s.Service AS ServerService,
            st.ManagementIPAddress1,
            st.ManagementIPAddress2,
            st.ServiceIPAddress1,
            st.ServiceIPAddress2,
            st.LUN,
            st.Capacity
        FROM Product p
        LEFT JOIN [Server] s ON p.SerialNumber = s.ServerSerialNumber
        LEFT JOIN Storage st ON p.SerialNumber = st.StorageSerialNumber
        WHERE p.CUserID = :customer_id
        ORDER BY p.SerialNumber
    """,
    
    # Customer Products (API - basit)
    "get_customer_products_api": """
        SELECT 
            p.SerialNumber,
            p.Name AS ProductName,
            p.MacAddress,
            p.FirmwareVersion,
            p.IsRepair,
            COALESCE(s.SeProductCode, st.SProductCode) AS ProductCode,
            CASE 
                WHEN s.ServerSerialNumber IS NOT NULL THEN 'Server'
                WHEN st.StorageSerialNumber IS NOT NULL THEN 'Storage'
                ELSE 'Other'
            END AS ProductType
        FROM Product p
        LEFT JOIN [Server] s ON p.SerialNumber = s.ServerSerialNumber
        LEFT JOIN Storage st ON p.SerialNumber = st.StorageSerialNumber
        WHERE p.CUserID = :customer_id
        ORDER BY p.SerialNumber
    """,
    
    # Product sayısı kontrolü
    "count_customer_products": """
        SELECT COUNT(*) as cnt FROM Product WHERE CUserID = :customer_id
    """,
    
    # Product kontrolü (repair request için)
    "check_product_for_repair": """
        SELECT SerialNumber, IsRepair
        FROM Product
        WHERE SerialNumber = :serial_number AND CUserID = :customer_id
    """,
    
    # RepairRequest oluştur
    "create_repair_request": """
        INSERT INTO RepairRequest (SerialNumber, Date, Status)
        OUTPUT INSERTED.RequestID
        VALUES (:serial_number, :request_date, 'NotAccepted')
    """,
    
    # RepairRequest oluştur (default status ile)
    "create_repair_request_default": """
        INSERT INTO RepairRequest (SerialNumber, Date)
        OUTPUT INSERTED.RequestID
        VALUES (:serial_number, :request_date)
    """,
    
    # Customer Repair Requests (tarih filtresi ile)
    "get_customer_repair_requests": """
        SELECT 
            rr.RequestID AS RepairRequestID,
            rr.Date AS RequestDate,
            rr.Status,
            rr.SerialNumber,
            p.Name
        FROM RepairRequest rr
        INNER JOIN Product p ON rr.SerialNumber = p.SerialNumber
        WHERE EXISTS (
            SELECT 1 FROM Product p2
            WHERE p2.SerialNumber = rr.SerialNumber AND p2.CUserID = :customer_id
        )
        {date_filter}
        ORDER BY rr.Date DESC
    """,
    
    # RepairRequest kontrolü (cancel için)
    "check_repair_request": """
        SELECT rr.RequestID AS RepairRequestID, rr.Status 
        FROM RepairRequest rr
        WHERE rr.RequestID = :repair_request_id 
        AND EXISTS (
            SELECT 1 FROM Product p
            WHERE p.SerialNumber = rr.SerialNumber AND p.CUserID = :customer_id
        )
    """,
    
    # RepairRequest iptal et
    "cancel_repair_request": """
        UPDATE RepairRequest
        SET Status = 'Cancelled'
        WHERE RequestID = :repair_request_id
    """,
    
    # Customer Feedback (tarih filtresi ile)
    "get_customer_feedback": """
        SELECT 
            cf.FeedbackID,
            vf.SaleID AS OrderID,
            vf.Rating,
            vf.FeedbackText,
            vf.Date AS FeedbackDate,
            o.SaleDate AS OrderDate
        FROM vw_CustomerFeedback vf
        INNER JOIN CustomerFeedBack cf ON vf.SaleID = cf.SaleID AND cf.CUserID = :customer_id
        LEFT JOIN [Order] o ON vf.SaleID = o.SaleID
        WHERE vf.CompanyTradeName = :customer_name
        {date_filter}
        ORDER BY vf.Date DESC
    """,
    
    # Order kontrolü (feedback için)
    "check_order_for_feedback": """
        SELECT o.SaleID 
        FROM [Order] o
        INNER JOIN Offer ofr ON o.OfferNo = ofr.OfferNo
        WHERE o.SaleID = :order_id AND ofr.CUserID = :customer_id
    """,
    
    # Feedback oluştur
    "create_feedback": """
        INSERT INTO CustomerFeedBack (SaleID, CUserID, Rating, FeedbackText, Date)
        OUTPUT INSERTED.FeedbackID
        VALUES (:sale_id, :customer_id, :rating, :feedback_text, :feedback_date)
    """,
    
    # Feedback kontrolü (update/delete için)
    "check_feedback": """
        SELECT FeedbackID FROM CustomerFeedBack
        WHERE FeedbackID = :feedback_id AND CUserID = :customer_id
    """,
    
    # Feedback güncelle
    "update_feedback": """
        UPDATE CustomerFeedBack
        SET Rating = :rating, FeedbackText = :feedback_text
        WHERE FeedbackID = :feedback_id
    """,
    
    # Feedback sil
    "delete_feedback": """
        DELETE FROM CustomerFeedBack
        WHERE FeedbackID = :feedback_id
    """,
}

# ============================================================================
# EMPLOYEE QUERIES
# ============================================================================

EMPLOYEE = {
    # Repair Requests listesi
    "get_repair_requests": """
        SELECT 
            rr.RequestID,
            rr.SerialNumber,
            rr.Date AS RequestDate,
            rr.Status,
            p.Name AS ProductName,
            p.MacAddress,
            p.FirmwareVersion
        FROM RepairRequest rr
        LEFT JOIN Product p ON rr.SerialNumber = p.SerialNumber
        ORDER BY rr.Date DESC
    """,
    
    # RepairRequest kontrolü
    "check_repair_request": """
        SELECT RequestID, Status
        FROM RepairRequest
        WHERE RequestID = :repair_request_id
    """,
    
    # RepairRequest kabul et
    "accept_repair_request": """
        UPDATE RepairRequest
        SET Status = 'Accepted'
        WHERE RequestID = :repair_request_id
    """,
    
    # RepairRequest reddet
    "reject_repair_request": """
        UPDATE RepairRequest
        SET Status = 'Rejected'
        WHERE RequestID = :repair_request_id
    """,
    
    # Technician kontrolü
    "check_technician": """
        SELECT TUserID
        FROM Technician
        WHERE TUserID = :technician_id
    """,
    
    # RepairRequest kolonlarını kontrol et
    "check_repair_request_columns": """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'RepairRequest'
    """,
    
    # RepairRequest'e teknisyen ata (TUserID varsa)
    "assign_technician_with_tuserid": """
        UPDATE RepairRequest
        SET TUserID = :technician_id, Status = 'InProgress'
        WHERE RequestID = :repair_request_id
    """,
    
    # RepairRequest'e teknisyen ata (TUserID yoksa)
    "assign_technician_without_tuserid": """
        UPDATE RepairRequest
        SET Status = 'InProgress'
        WHERE RequestID = :repair_request_id
    """,
    
    # Technician listesi
    "get_technicians": """
        SELECT 
            t.EUserID AS TechnicianID,
            e.FirstName,
            e.LastName
        FROM Technician t
        INNER JOIN Employee e ON t.EUserID = e.EUserID
        ORDER BY e.FirstName, e.LastName
    """,
    
    # Technician kontrolü (EUserID ile)
    "check_technician_by_euserid": """
        SELECT EUserID
        FROM Technician
        WHERE EUserID = :technician_id
    """,
    
    # Repair oluştur
    "create_repair": """
        INSERT INTO Repair (RequestID, StartDate, Response, TEUserID)
        OUTPUT INSERTED.RepairID
        VALUES (:repair_request_id, GETDATE(), 'NOT COMPLETED', :technician_id)
    """,
    
    # Repair kontrolü
    "check_repair": """
        SELECT RepairID, Response
        FROM Repair
        WHERE RepairID = :repair_id
    """,
    
    # Repair tamamla
    "complete_repair": """
        UPDATE Repair
        SET Response = 'COMPLETED'
        WHERE RepairID = :repair_id
    """,
    
    # Order kontrolü
    "check_order": """
        SELECT SaleID
        FROM [Order]
        WHERE SaleID = :order_id
    """,
    
    # Order status güncelle
    "update_order_status": """
        UPDATE [Order]
        SET Status = :status
        WHERE SaleID = :order_id
    """,
    
    # ============================================================================
    # PRODUCT & INVENTORY MANAGEMENT
    # ============================================================================
    
    # ProductInventory kontrolü
    "check_product_inventory_exists": """
        SELECT ProductCode FROM ProductInventory WHERE ProductCode = :product_code
    """,
    
    # ProductInventory ekle (genel) - Stok değerleri trigger'lar ile otomatik belirlenecek
    "create_product_inventory": """
        INSERT INTO ProductInventory (ProductCode, ProductDescription, PurchaseUnitPrice, ProductType)
        VALUES (:product_code, :product_description, :purchase_unit_price, :product_type)
    """,
    
    # ServerInventory ekle
    "create_server_inventory": """
        INSERT INTO ServerInventory (SeProductCode, CPU, RAM, Disk)
        VALUES (:product_code, :cpu, :ram, :disk)
    """,
    
    # StorageInventory ekle
    "create_storage_inventory": """
        INSERT INTO StorageInventory (SProductCode, DiskType, DiskSpace, DiskCount)
        VALUES (:product_code, :disk_type, :disk_space, :disk_count)
    """,
    
    # Server ekle
    "create_server": """
        INSERT INTO [Server] (ServerSerialNumber, IPAddress, OperatingSystem, Service, SeProductCode)
        VALUES (:serial_number, :ip_address, :operating_system, :service, :product_code)
    """,
    
    # Storage ekle
    "create_storage": """
        INSERT INTO Storage (StorageSerialNumber, ManagementIPAddress1, ManagementIPAddress2, ServiceIPAddress1, ServiceIPAddress2, LUN, Capacity, SProductCode)
        VALUES (:serial_number, :mgmt_ip1, :mgmt_ip2, :service_ip1, :service_ip2, :lun, :capacity, :product_code)
    """,
    
    # Product ekle (genel)
    "create_product": """
        INSERT INTO Product (SerialNumber, Name, MacAddress, FirmwareVersion, IsRepair, CUserID)
        VALUES (:serial_number, :name, :mac_address, :firmware_version, :is_repair, :c_user_id)
    """,
    
    # Product kontrolü (SerialNumber)
    "check_product_exists": """
        SELECT SerialNumber FROM Product WHERE SerialNumber = :serial_number
    """,
    
    # Server kontrolü
    "check_server_exists": """
        SELECT ServerSerialNumber FROM [Server] WHERE ServerSerialNumber = :serial_number
    """,
    
    # Storage kontrolü
    "check_storage_exists": """
        SELECT StorageSerialNumber FROM Storage WHERE StorageSerialNumber = :serial_number
    """,
    
    # ProductCode kontrolü (ServerInventory)
    "check_server_inventory_exists": """
        SELECT SeProductCode FROM ServerInventory WHERE SeProductCode = :product_code
    """,
    
    # ProductCode kontrolü (StorageInventory)
    "check_storage_inventory_exists": """
        SELECT SProductCode FROM StorageInventory WHERE SProductCode = :product_code
    """,
    
    # MacAddress kontrolü
    "check_mac_address_exists": """
        SELECT SerialNumber FROM Product WHERE MacAddress = :mac_address
    """,
}

# ============================================================================
# PROFILE QUERIES
# ============================================================================

PROFILE = {
    # Employee bilgileri
    "get_employee": """
        SELECT e.*, d.Name AS DepartmentName
        FROM Employee e
        LEFT JOIN SalariedEmployee se ON e.EUserID = se.EUserID
        LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
        WHERE e.EUserID = :user_id
    """,
    
    # SalariedEmployee bilgileri
    "get_salaried_employee": """
        SELECT se.*, d.Name AS DepartmentName
        FROM SalariedEmployee se
        LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
        WHERE se.EUserID = :user_id
    """,
    
    # Employee telefon numaraları
    "get_employee_telno": """
        SELECT TelCode, TelNo, 
               CASE 
                   WHEN TelCode IS NOT NULL AND TelNo IS NOT NULL THEN TelCode + ' ' + TelNo
                   WHEN TelNo IS NOT NULL THEN TelNo
                   ELSE NULL
               END AS FullTelNo
        FROM [E-TelNo]
        WHERE EUserID = :user_id
    """,
    
    # E-MailAdress kolonlarını bul
    "get_email_columns": """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'E-MailAdress'
        ORDER BY ORDINAL_POSITION
    """,
    
    # Employee email adresleri
    "get_employee_emails": """
        SELECT [{email_column}]
        FROM [E-MailAdress]
        WHERE EUserID = :user_id
    """,
    
    # User bilgileri
    "get_user": """
        SELECT UserID, RegisterDate, UserType
        FROM [User]
        WHERE UserID = :user_id
    """,
    
    # Customer bilgileri
    "get_customer": """
        SELECT c.*
        FROM CustomerCompany c
        WHERE c.CUserID = :user_id
    """,
    
    # Customer iletişim kişileri
    "get_customer_contacts": """
        SELECT MailAddress, CUserID, DepartmentName, TelCode, TelNo, FirstName, MiddleName, LastName,
               CASE 
                   WHEN TelCode IS NOT NULL AND TelNo IS NOT NULL THEN TelCode + ' ' + TelNo
                   WHEN TelNo IS NOT NULL THEN TelNo
                   ELSE NULL
               END AS FullTelNo,
               CASE 
                   WHEN MiddleName IS NOT NULL THEN FirstName + ' ' + MiddleName + ' ' + LastName
                   ELSE FirstName + ' ' + LastName
               END AS FullName
        FROM CommunityCompany
        WHERE CUserID = :user_id
        ORDER BY DepartmentName, LastName, FirstName
    """,
    
    # Employee profil güncelle
    "update_employee": """
        UPDATE Employee
        SET {update_fields}
        WHERE EUserID = :user_id
    """,
    
    # Telefon numarası ekle (Employee)
    "add_employee_telno": """
        INSERT INTO [E-TelNo] (EUserID, TelCode, TelNo)
        VALUES (:user_id, :telcode, :telno)
    """,
    
    # Telefon numarası sil (Employee - TelCode ile)
    "delete_employee_telno_with_code": """
        DELETE FROM [E-TelNo]
        WHERE EUserID = :user_id AND TelCode = :telcode AND TelNo = :telno
    """,
    
    # Telefon numarası sil (Employee - sadece TelNo)
    "delete_employee_telno": """
        DELETE FROM [E-TelNo]
        WHERE EUserID = :user_id AND TelNo = :telno
    """,
    
    # Email adresi ekle (Employee)
    "add_employee_email": """
        INSERT INTO [E-MailAdress] (EUserID, [{email_column}])
        VALUES (:user_id, :email)
    """,
    
    # Email adresi sil (Employee)
    "delete_employee_email": """
        DELETE FROM [E-MailAdress]
        WHERE EUserID = :user_id AND [{email_column}] = :email
    """,
    
    # Customer iletişim kişisi ekle
    "add_customer_contact": """
        INSERT INTO CommunityCompany (MailAddress, CUserID, DepartmentName, TelCode, TelNo, FirstName, MiddleName, LastName)
        VALUES (:mail_address, :customer_id, :department_name, :telcode, :telno, :first_name, :middle_name, :last_name)
    """,
    
    # Customer iletişim kişisi sil
    "delete_customer_contact": """
        DELETE FROM CommunityCompany
        WHERE MailAddress = :mail_address AND CUserID = :customer_id
    """,
    
    # Customer iletişim kişisi güncelle (MailAddress değiştiyse)
    "update_customer_contact_delete": """
        DELETE FROM CommunityCompany
        WHERE MailAddress = :old_mail_address AND CUserID = :customer_id
    """,
    
    # Customer iletişim kişisi güncelle (yeni kayıt)
    "update_customer_contact_insert": """
        INSERT INTO CommunityCompany (MailAddress, CUserID, DepartmentName, TelCode, TelNo, FirstName, MiddleName, LastName)
        VALUES (:mail_address, :customer_id, :department_name, :telcode, :telno, :first_name, :middle_name, :last_name)
    """,
    
    # Customer iletişim kişisi güncelle (MailAddress aynıysa)
    "update_customer_contact": """
        UPDATE CommunityCompany
        SET DepartmentName = :department_name,
            TelCode = :telcode,
            TelNo = :telno,
            FirstName = :first_name,
            MiddleName = :middle_name,
            LastName = :last_name
        WHERE MailAddress = :mail_address AND CUserID = :customer_id
    """,
    
    # Şifre kontrolü
    "check_password": """
        SELECT Password
        FROM [User]
        WHERE UserID = :user_id
    """,
    
    # Şifre güncelle
    "update_password": """
        UPDATE [User]
        SET Password = :new_password
        WHERE UserID = :user_id
    """,
}

# ============================================================================
# TABLES QUERIES
# ============================================================================

TABLES = {
    # HR kontrolü
    "check_hr_department": """
        SELECT d.Name
        FROM Employee e
        JOIN SalariedEmployee se ON e.EUserID = se.EUserID
        JOIN Department d ON se.DepartmentNo = d.DepartmentNo
        WHERE e.EUserID = :user_id
    """,
    
    # View listesi (employee için)
    "get_views_for_employee": """
        SELECT 
            s.name AS schema_name,
            v.name AS view_name,
            QUOTENAME(s.name) + '.' + QUOTENAME(v.name) AS full_name
        FROM sys.views v
        JOIN sys.schemas s ON v.schema_id = s.schema_id
        WHERE v.is_ms_shipped = 0
        AND v.name IN ({view_list})
        ORDER BY s.name, v.name
    """,
    
    # View listesi (customer için)
    "get_views_for_customer": """
        SELECT 
            s.name AS schema_name,
            v.name AS view_name,
            QUOTENAME(s.name) + '.' + QUOTENAME(v.name) AS full_name
        FROM sys.views v
        JOIN sys.schemas s ON v.schema_id = s.schema_id
        WHERE v.is_ms_shipped = 0
        AND v.name IN ({view_list})
        ORDER BY s.name, v.name
    """,
    
    # Tablo/View var mı kontrol et
    "check_table_exists": """
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
    """,
    
    # View var mı kontrol et
    "check_view_exists": """
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
    """,
    
    # Tablo kolonlarını al
    "get_table_columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
        ORDER BY ORDINAL_POSITION
    """,
    
    # Tablo verilerini al (arama ile)
    "get_table_data": """
        SELECT * FROM [{schema}].[{table_name}]
        {where_clause}
        ORDER BY (SELECT NULL)
        OFFSET :offset ROWS
        FETCH NEXT :limit ROWS ONLY
    """,
    
    # Toplam kayıt sayısı (arama ile)
    "count_table_data": """
        SELECT COUNT(*) FROM [{schema}].[{table_name}]
        {where_clause}
    """,
    
    # Primary key bul
    "get_primary_key": """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = :schema 
        AND TABLE_NAME = :table_name
        AND OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
    """,
    
    # Employee TC'den EUserID bul
    "get_employee_id_by_tc": """
        SELECT EUserID FROM Employee WHERE TC = :tc
    """,
    
    # Department Name'den DepartmentNo bul
    "get_department_no": """
        SELECT DepartmentNo FROM Department WHERE Name = :dept_name
    """,
    
    # Tablo güncelle (normal)
    "update_table_record": """
        UPDATE [{schema}].[{table_name}]
        SET {set_clauses}
        WHERE [{primary_key}] = :primary_key_value
    """,
    
    # SalariedEmployee güncelle
    "update_salaried_employee": """
        UPDATE [dbo].[SalariedEmployee]
        SET {set_clauses}
        WHERE EUserID = :employee_id
    """,
    
    # Technician güncelle
    "update_technician": """
        UPDATE [dbo].[Technician]
        SET {set_clauses}
        WHERE EUserID = :employee_id
    """,
    
    # Employee bilgileri (yetki kontrolü için)
    "get_employee_for_permission": """
        SELECT d.Name AS Department
        FROM Employee e
        INNER JOIN SalariedEmployee se ON e.EUserID = se.EUserID
        LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
        WHERE e.EUserID = :user_id
    """,
    
    # SalariedEmployee var mı kontrol et
    "check_salaried_employee": """
        SELECT COUNT(*) as cnt
        FROM SalariedEmployee
        WHERE EUserID = :user_id
    """,
    
    # Offer oluştur
    "create_offer": """
        INSERT INTO Offer (CUserID, ExchangeRate, PaymentTerm, Term)
        OUTPUT INSERTED.OfferNo
        VALUES (:customer_id, :exchange_rate, :payment_term, :term)
    """,
    
    # Customer kontrolü
    "check_customer": """
        SELECT CUserID FROM CustomerCompany WHERE CUserID = :customer_id
    """,
    
    # Offer kontrolü
    "check_offer": """
        SELECT OfferNo FROM Offer WHERE OfferNo = :offer_no
    """,
    
    # Product kontrolü
    "check_product": """
        SELECT ProductCode FROM ProductInventory WHERE ProductCode = :product_code
    """,
    
    # OfferLine ekle
    "add_offer_line": """
        INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice)
        VALUES (:offer_no, :product_code, :quantity, :sales_unit_price)
    """,
    
    # Customer listesi
    "get_customers": """
        SELECT CUserID, CompanyTradeName
        FROM CustomerCompany
        ORDER BY CompanyTradeName
    """,
    
    # Product listesi
    "get_products": """
        SELECT ProductCode, ProductDescription
        FROM ProductInventory
        ORDER BY ProductCode
    """,
}

# ============================================================================
# AUTH QUERIES
# ============================================================================

AUTH = {
    # Employee authentication (stored procedure)
    "authenticate_employee": """
        EXEC sp_AuthenticateEmployee @TC = :tc
    """,
    
    # Customer authentication (stored procedure)
    "authenticate_customer": """
        EXEC sp_AuthenticateCustomer @RegistryNo = :registry_no
    """,
    
    # TC kontrolü (register için)
    "check_tc_exists": """
        SELECT EUserID FROM Employee WHERE TC = :tc
    """,
    
    # Employee register (stored procedure)
    "register_employee": """
        EXEC sp_RegisterSalariedEmployee 
            @Password = :password,
            @TC = :tc,
            @FirstName = :first_name,
            @MiddleName = :middle_name,
            @LastName = :last_name,
            @BirthDate = :birth_date,
            @HiredDate = :hired_date,
            @DepartmentName = :department_name
    """,
    
    # Trade Registry Number kontrolü (register için)
    "check_registry_exists": """
        SELECT CUserID FROM CustomerCompany WHERE TradeRegistryNumber = :registry_no
    """,
    
    # Customer register (stored procedure)
    "register_customer": """
        EXEC sp_RegisterCustomerCompany 
            @Password = :password,
            @TradeRegistryNumber = :registry_no,
            @CompanyTradeName = :company_trade_name,
            @Website = :website,
            @YearOfEstablishment = :year_of_establishment,
            @TaxOffice = :tax_office,
            @TaxNumber = :tax_number
    """,
    
    # Department listesi
    "get_departments": """
        SELECT DepartmentNo, Name 
        FROM [Department] 
        WHERE Name IS NOT NULL
        ORDER BY DepartmentNo
    """,
}


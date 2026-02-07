USE ServicePool3;
GO

-- =============================================
-- 1. ADRES & LOKASYONLAR (15 Kayýt)
-- =============================================
INSERT INTO [Address] (Country, City, PostalCode, FullAddress, AddressType) VALUES 
('Turkey', 'Istanbul', 34394, 'Buyukdere Cad. No:199 Levent', 'HQ'),
('Turkey', 'Ankara', 06510, 'Cukurambar Mah. 1453. Cad.', 'Branch'),
('Turkey', 'Izmir', 35100, 'Folkart Towers Bayrakli', 'Branch'),
('Germany', 'Berlin', 10117, 'Unter den Linden 6', 'Office'),
('Germany', 'Munich', 80331, 'Marienplatz 1', 'Office'),
('USA', 'New York', 10007, '250 Greenwich St', 'HQ'),
('USA', 'San Francisco', 94105, 'Salesforce Tower', 'Branch'),
('UK', 'London', 55102, 'Canary Wharf', 'Office'),
('France', 'Paris', 75008, 'Champs-Elysees', 'Office'),
('Turkey', 'Bursa', 16000, 'Nilufer Organize Sanayi', 'Warehouse'),
('Turkey', 'Antalya', 07000, 'Konyaalti Teknokent', 'Office'),
('Netherlands', 'Amsterdam', 1012, 'Dam Square 5', 'Branch'),
('Turkey', 'Istanbul', 34000, 'Kadikoy Moda Cad.', 'Home'),
('Turkey', 'Istanbul', 34000, 'Besiktas Carsisi', 'Home'),
('USA', 'Seattle', 98109, 'Amazon Sphere', 'Customer');

-- =============================================
-- 2. KULLANICILAR (User Table - 20 Kayýt)
-- Identity ID tahmini: 1-20 arasý
-- =============================================
INSERT INTO [User] (Password, UserType, AddressID) VALUES
-- Çalýþanlar (1-10)
('EmpPass1!', 'Employee', 1), -- 1: CEO
('EmpPass2!', 'Employee', 1), -- 2: Sales Manager
('EmpPass3!', 'Employee', 2), -- 3: Sales Rep
('EmpPass4!', 'Employee', 3), -- 4: Tech Lead
('EmpPass5!', 'Employee', 1), -- 5: Technician
('EmpPass6!', 'Employee', 2), -- 6: Technician
('EmpPass7!', 'Employee', 3), -- 7: Technician
('EmpPass8!', 'Employee', 10),-- 8: Warehouse Mngr
('EmpPass9!', 'Employee', 1), -- 9: HR Specialist
('EmpPass0!', 'Employee', 4), -- 10: Germany Rep
-- Müþteriler (11-20)
('CustPass1', 'CustomerCompany', 6), -- 11
('CustPass2', 'CustomerCompany', 7), -- 12
('CustPass3', 'CustomerCompany', 8), -- 13
('CustPass4', 'CustomerCompany', 11),-- 14
('CustPass5', 'CustomerCompany', 12),-- 15
('CustPass6', 'CustomerCompany', 15),-- 16
('CustPass7', 'CustomerCompany', 5), -- 17
('CustPass8', 'CustomerCompany', 9), -- 18
('CustPass9', 'CustomerCompany', 2), -- 19
('CustPass0', 'CustomerCompany', 3); -- 20

-- =============================================
-- 3. ÇALIÞAN DETAYLARI (Employee)
-- =============================================
INSERT INTO [Employee] (EUserID, TC, FirstName, LastName, BirthDate, HiredDate, EmployeeType) VALUES
(1, '10000000001', 'Hakan', 'Yonetici', '1975-05-20', '2015-01-01', 'Manager'),
(2, '10000000002', 'Selin', 'Satis', '1982-08-15', '2016-03-10', 'Sales'),
(3, '10000000003', 'Burak', 'Pazarlama', '1990-11-02', '2018-06-01', 'Sales'),
(4, '10000000004', 'Tekin', 'Basmuhendis', '1985-02-28', '2017-02-15', 'Technical'),
(5, '10000000005', 'Ali', 'Tamirci', '1995-04-10', '2020-09-01', 'Technician'),
(6, '10000000006', 'Veli', 'Kablolama', '1996-07-22', '2021-01-15', 'Technician'),
(7, '10000000007', 'Ayse', 'Sistemci', '1993-12-05', '2019-11-20', 'Technician'),
(8, '10000000008', 'Depo', 'Sorumlusu', '1980-03-30', '2015-05-05', 'Operations'),
(9, '10000000009', 'Zeynep', 'InsanK', '1991-09-09', '2018-01-01', 'HR'),
(10,'10000000010', 'Hans', 'Mueller', '1988-06-14', '2019-04-01', 'Sales');

-- =============================================
-- 4. ALT TÝPLER: Technician & SalariedEmployee
-- (Döngüsel Baðýmlýlýk için DepartmentNo önce NULL girilir)
-- =============================================

-- Teknisyenler (Saatlik çalýþanlar)
INSERT INTO Technician (EUserID, HourlySalary) VALUES
(5, 45.00), -- Ali
(6, 40.00), -- Veli
(7, 50.00); -- Ayse

-- Maaþlýlar (Maaþ + Departman)
-- Manager ID'leri henüz olmadýðý için NULL veya mantýksal hiyerarþi kuruyoruz.
INSERT INTO SalariedEmployee (EUserID, Salary, MEUserID, DepartmentNo) VALUES
(1, 15000.00, NULL, NULL), -- CEO (Müdürü yok)
(2, 8000.00, 1, NULL),    -- Sales Manager (Müdürü CEO)
(3, 5000.00, 2, NULL),    -- Sales Rep (Müdürü Sales Manager)
(4, 9000.00, 1, NULL),    -- Tech Lead (Müdürü CEO)
(8, 4500.00, 1, NULL),    -- Warehouse (Müdürü CEO)
(9, 4000.00, 1, NULL),    -- HR (Müdürü CEO)
(10,5500.00, 2, NULL);    -- Germany Sales (Müdürü Sales Manager)

-- =============================================
-- 5. DEPARTMANLAR (Departments)
-- =============================================
INSERT INTO Department (Name, MngrSUserID) VALUES
('Executive Board', 1),    -- Dept 1
('Sales & Marketing', 2),  -- Dept 2
('Technical Services', 4), -- Dept 3
('Human Resources', 9),    -- Dept 4
('Operations', 8);         -- Dept 5

-- =============================================
-- 6. ÇALIÞANLARI GÜNCELLEME (Departman Atama)
-- =============================================
UPDATE SalariedEmployee SET DepartmentNo = 1 WHERE EUserID = 1;
UPDATE SalariedEmployee SET DepartmentNo = 2 WHERE EUserID IN (2, 3, 10);
UPDATE SalariedEmployee SET DepartmentNo = 3 WHERE EUserID = 4;
UPDATE SalariedEmployee SET DepartmentNo = 5 WHERE EUserID = 8;
UPDATE SalariedEmployee SET DepartmentNo = 4 WHERE EUserID = 9;

-- =============================================
-- 7. MÜÞTERÝLER (CustomerCompany)
-- =============================================
INSERT INTO CustomerCompany (CUserID, TradeRegistryNumber, CompanyTradeName, Website, YearOfEstablishment, TaxOffice, TaxNumber) VALUES
(11, 'US-NY-001', 'Global Finance Corp', 'www.gfc.com', 1990, 'NY Tax', 'TAX-US-01'),
(12, 'US-CA-002', 'Silicon Valley Tech', 'www.svt.io', 2010, 'CA Tax', 'TAX-US-02'),
(13, 'UK-LDN-003', 'London Bridge Trading', 'www.lbt.uk', 2005, 'London', 'TAX-UK-01'),
(14, 'TR-ANT-004', 'Akdeniz Turizm A.S.', 'www.akdeniz.com.tr', 1998, 'Antalya', 'VERGI-01'),
(15, 'NL-AMS-005', 'Dutch Logistics', 'www.dutchlog.nl', 2012, 'Amsterdam', 'TAX-NL-01'),
(16, 'US-SEA-006', 'Cloud Services Inc', 'www.cloudserv.com', 2015, 'Seattle', 'TAX-US-03'),
(17, 'TR-IST-007', 'Bosphorus Data', 'www.bosphorus.tech', 2020, 'Maslak', 'VERGI-02'),
(18, 'TR-BUR-008', 'Otomotiv Yan Sanayi', 'www.oys.com.tr', 1985, 'Bursa', 'VERGI-03'),
(19, 'DE-BER-009', 'Berlin Startups Gmbh', 'www.berlinstart.de', 2022, 'Berlin', 'TAX-DE-01'),
(20, 'TR-IZM-010', 'Ege Yazilim', 'www.egeyazilim.com', 2018, 'Kordon', 'VERGI-04');

-- =============================================
-- 8. ÝLETÝÞÝM (Email, TelNo, Community)
-- =============================================
INSERT INTO [E-MailAdress] (EUserID, MailAddress) VALUES
(1, 'hakan@servicepool.com'), (2, 'selin@servicepool.com'), (3, 'burak@servicepool.com'),
(4, 'tekin@servicepool.com'), (5, 'ali@servicepool.com'), (11, 'contact@gfc.com'),
(12, 'info@svt.io'), (13, 'procurement@lbt.uk');

INSERT INTO [E-TelNo] (EUserID, TelCode, TelNo) VALUES
(1, '+90', '5321111111'), (2, '+90', '5322222222'), (5, '+90', '5325555555'),
(11, '+1', '2125550100'), (12, '+1', '4155550200');

INSERT INTO CommunityCompany (MailAddress, CUserID, DepartmentName, TelCode, TelNo, FirstName, LastName, MiddleName) VALUES
('john.doe@gfc.com', 11, 'IT Purchasing', '+1', '2129990001', 'John', 'Doe', NULL),
('jane.smith@svt.io', 12, 'CTO Office', '+1', '4159990002', 'Jane', 'Smith', 'Ann'),
('ahmet@akdeniz.com', 14, 'Satin Alma', '+90', '2423330000', 'Ahmet', 'Yilmaz', NULL);

-- =============================================
-- 9. ENVANTER TANIMLARI (Product/Storage/Server Inventory)
-- =============================================

-- Server Tipleri
INSERT INTO ServerInventory (SeProductCode, CPU, RAM, Disk) VALUES
('SRV-HIGH-01', 128, 1024, '4x2TB NVMe'),
('SRV-MID-01', 64, 512, '2x1TB SSD'),
('SRV-LOW-01', 16, 64, '1x500GB SSD'),
('SRV-BLADE-X', 32, 256, 'Diskless');

-- Storage Tipleri
INSERT INTO StorageInventory (SProductCode, DiskType, DiskSpace, DiskCount) VALUES
('STO-FLASH-X', 'SSD', '50TB', 24),
('STO-HYBRID-Y', 'SAS', '200TB', 48),
('STO-ARCHIVE-Z', 'HDD', '1PB', 96);

-- Genel Envanter (Inventory Triggerlarý için önce bunlar olmalý)
INSERT INTO ProductInventory (ProductCode, ProductDescription, PurchaseUnitPrice, ProductType) VALUES
('SRV-HIGH-01', 'Super Computer Cluster Node', 12000.00, 'Server'),
('SRV-MID-01', 'Enterprise Rack Server', 6000.00, 'Server'),
('SRV-LOW-01', 'Entry Level Server', 2500.00, 'Server'),
('SRV-BLADE-X', 'Blade Server Module', 4000.00, 'Server'),
('STO-FLASH-X', 'All-Flash Array', 25000.00, 'Storage'),
('STO-HYBRID-Y', 'Hybrid Storage System', 15000.00, 'Storage'),
('STO-ARCHIVE-Z', 'Cold Storage System', 10000.00, 'Storage');

-- =============================================
-- 10. FÝZÝKSEL ÜRÜNLER (Products - Base Table + Subtypes)
-- Not: Triggerlar AvailableStock'u artýracak.
-- =============================================

-- Base Product Ekleme (Henüz satýlmadý CUserID = NULL)
-- 20 Tane ürün oluþturuyoruz.
INSERT INTO Product (SerialNumber, Name, MacAddress, FirmwareVersion, IsRepair, CUserID) VALUES
-- Serverlar
('SN-SRV-101', 'HighPerf Node 1', 'AA:00:00:00:01', 'v2.1', 0, NULL),
('SN-SRV-102', 'HighPerf Node 2', 'AA:00:00:00:02', 'v2.1', 0, NULL),
('SN-SRV-103', 'HighPerf Node 3', 'AA:00:00:00:03', 'v2.1', 0, NULL),
('SN-SRV-201', 'MidRange SRV 1', 'BB:00:00:00:01', 'v1.5', 0, NULL),
('SN-SRV-202', 'MidRange SRV 2', 'BB:00:00:00:02', 'v1.5', 0, NULL),
('SN-SRV-203', 'MidRange SRV 3', 'BB:00:00:00:03', 'v1.5', 0, NULL),
('SN-SRV-204', 'MidRange SRV 4', 'BB:00:00:00:04', 'v1.5', 0, NULL),
('SN-SRV-301', 'Entry SRV 1',    'CC:00:00:00:01', 'v1.0', 0, NULL),
('SN-SRV-302', 'Entry SRV 2',    'CC:00:00:00:02', 'v1.0', 0, NULL),
('SN-SRV-401', 'Blade Mod 1',    'DD:00:00:00:01', 'v3.0', 0, NULL),
-- Storagelar
('SN-STO-501', 'Flash Array A',  'EE:00:00:00:01', 'v4.2', 0, NULL),
('SN-STO-502', 'Flash Array B',  'EE:00:00:00:02', 'v4.2', 0, NULL),
('SN-STO-601', 'Hybrid STO A',   'FF:00:00:00:01', 'v2.8', 0, NULL),
('SN-STO-602', 'Hybrid STO B',   'FF:00:00:00:02', 'v2.8', 0, NULL),
('SN-STO-701', 'Archive STO A',  '00:11:22:33:44', 'v1.1', 0, NULL);

-- Subtype Ekleme (Triggerlar AvailableStock'u güncelleyecek)
INSERT INTO [Server] (ServerSerialNumber, IPAddress, OperatingSystem, Service, SeProductCode) VALUES
('SN-SRV-101', '10.10.10.1', 'RHEL 8', 'Cluster Master', 'SRV-HIGH-01'),
('SN-SRV-102', '10.10.10.2', 'RHEL 8', 'Cluster Node', 'SRV-HIGH-01'),
('SN-SRV-103', '10.10.10.3', 'RHEL 8', 'Cluster Node', 'SRV-HIGH-01'),
('SN-SRV-201', '192.168.1.10', 'Windows 2019', 'AD DC', 'SRV-MID-01'),
('SN-SRV-202', '192.168.1.11', 'Windows 2019', 'File Srv', 'SRV-MID-01'),
('SN-SRV-203', '192.168.1.12', 'Ubuntu 20.04', 'Web Srv', 'SRV-MID-01'),
('SN-SRV-204', '192.168.1.13', 'Ubuntu 20.04', 'App Srv', 'SRV-MID-01'),
('SN-SRV-301', '192.168.5.5', 'CentOS 7', 'Backup', 'SRV-LOW-01'),
('SN-SRV-302', '192.168.5.6', 'CentOS 7', 'Proxy', 'SRV-LOW-01'),
('SN-SRV-401', '172.16.0.1', 'ESXi 7.0', 'Virtualization', 'SRV-BLADE-X');

INSERT INTO Storage (StorageSerialNumber, ManagementIPAddress1, ManagementIPAddress2, ServiceIPAddress1, ServiceIPAddress2, LUN, Capacity, SProductCode) VALUES
('SN-STO-501', '10.0.0.1', '10.0.0.2', '10.1.0.1', '10.1.0.2', 'LUN01', 51200, 'STO-FLASH-X'),
('SN-STO-502', '10.0.0.3', '10.0.0.4', '10.1.0.3', '10.1.0.4', 'LUN02', 51200, 'STO-FLASH-X'),
('SN-STO-601', '10.0.0.5', '10.0.0.6', '10.1.0.5', '10.1.0.6', 'LUN03', 204800, 'STO-HYBRID-Y'),
('SN-STO-602', '10.0.0.7', '10.0.0.8', '10.1.0.7', '10.1.0.8', 'LUN04', 204800, 'STO-HYBRID-Y'),
('SN-STO-701', '10.0.0.9', '10.0.0.10', '10.1.0.9', '10.1.0.10', 'LUN05', 1048576, 'STO-ARCHIVE-Z');

INSERT INTO StorageWWN (StorageSerialNumber, WWN) VALUES
('SN-STO-501', '50:00:00:01:00:00:00:0A'),
('SN-STO-601', '50:00:00:01:00:00:00:0B');

-- =============================================
-- 11. TEKLÝFLER (Offer & OfferLine) - 6 Adet
-- Not: Triggerlar fiyatlarý ve karlarý otomatik hesaplayacak.
-- =============================================

-- Teklif 1: Kabul Edilmiþ (Büyük Satýþ)
INSERT INTO Offer (CUserID, ExchangeRate, Status, PaymentTerm, Term) VALUES (11, 34.20, 'Accepted', '2026-02-01', '60 Days');
INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice) VALUES (1, 'SRV-HIGH-01', 2, 18000.00); -- 2 Sunucu

-- Teklif 2: Kabul Edilmiþ (Storage Satýþý)
INSERT INTO Offer (CUserID, ExchangeRate, Status, PaymentTerm, Term) VALUES (12, 34.25, 'Accepted', '2026-01-15', 'Cash');
INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice) VALUES (2, 'STO-FLASH-X', 1, 35000.00); 

-- Teklif 3: Reddedilmiþ (Pahalý Gelmiþ)
INSERT INTO Offer (CUserID, ExchangeRate, Status, PaymentTerm, Term) VALUES (13, 34.30, 'Rejected', '2026-03-01', '30 Days');
INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice) VALUES (3, 'STO-ARCHIVE-Z', 1, 15000.00); -- Karj marjý yüksek tutulmuþ

-- Teklif 4: Kabul Edilmiþ (Karma Satýþ)
INSERT INTO Offer (CUserID, ExchangeRate, Status, PaymentTerm, Term) VALUES (17, 34.50, 'Accepted', '2026-01-20', 'Credit Card');
INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice) VALUES 
(4, 'SRV-MID-01', 3, 8000.00),
(4, 'STO-HYBRID-Y', 1, 18000.00);

-- Teklif 5: Beklemede (Henüz NotAccepted)
INSERT INTO Offer (CUserID, ExchangeRate, Status, PaymentTerm, Term) VALUES (15, 34.10, 'NotAccepted', '2026-04-01', '90 Days');
INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice) VALUES (5, 'SRV-LOW-01', 5, 3000.00);

-- =============================================
-- 12. SÝPARÝÞLER (Orders) - 3 Adet
-- Not: Trigger çalýþacak. Product tablosundaki ürünler sahiplendirilecek (CUserID atanacak).
-- Stoklar Reserved -> Field'a düþecek.
-- =============================================

-- Sipariþ 1 (Teklif 1'e istinaden) -> 2 tane SRV-HIGH-01 satýlýr.
INSERT INTO [Order] (PaymentType, DailyUSDExchangeRate, OfferNo, SEUserID, SaleDate) VALUES
('Transfer', 34.22, 1, 2, '2025-01-10');

-- Sipariþ 2 (Teklif 2'ye istinaden) -> 1 tane STO-FLASH-X satýlýr.
INSERT INTO [Order] (PaymentType, DailyUSDExchangeRate, OfferNo, SEUserID, SaleDate) VALUES
('Transfer', 34.28, 2, 3, '2025-01-12');

-- Sipariþ 3 (Teklif 4'e istinaden) -> 3 SRV-MID-01 + 1 STO-HYBRID-Y satýlýr.
INSERT INTO [Order] (PaymentType, DailyUSDExchangeRate, OfferNo, SEUserID, SaleDate) VALUES
('CreditCard', 34.55, 4, 2, '2025-01-15');

-- =============================================
-- 13. GERÝ BÝLDÝRÝMLER (CustomerFeedBack)
-- =============================================
INSERT INTO CustomerFeedBack (SaleID, CUserID, Rating, FeedbackText) VALUES
(1, 11, 5, 'Performance is outstanding. Delivery was on time.'),
(2, 12, 4, 'Good storage unit but setup was tricky.'),
(3, 17, 5, 'Perfect integration with our existing systems.');

-- =============================================
-- 14. TAMÝR DÖNGÜSÜ (RepairRequest & Repair)
-- Senaryo: Sipariþ 1'de satýlan ürünlerden biri arýzalandý.
-- Sipariþ 1'de satýlan ürünleri bulmak için: (User 11'e ait ürünler)
-- =============================================

-- Bir ürünün seri numarasýný "Satýlmýþ" olarak simüle edip arýza kaydý açalým.
-- Normalde Order triggerý CUserID atadý, o yüzden User 11'e ait bir seri numarasý seçiyoruz.
-- Bu örnek için manuel bir seri numarasý seçimi yerine, mantýken satýlan bir numarayý yazýyorum.
-- Scriptin deterministik olmasý için, Order triggerýnýn rasgele seçtiði seri numaralarýný tahmin edemeyiz.
-- O yüzden buradaki 'SN-SRV-101' in ORDER triggerý tarafýndan User 11'e satýldýðýný varsayýyoruz
-- (Eðer trigger rasgele baþka birini seçtiyse bu insert hata vermez ama mantýken tutarsýz olabilir.
-- Gerçek hayatta UI'dan seçilir). 
-- *Garanti olsun diye* manuel bir update ile bir ürünü müþteriye bozup tamire alalým:

-- SENARYO: 'SN-SRV-101' CUserID=11'e satýlmýþ olsun (Trigger yapmýþ olabilir, biz garantiye alalým)
UPDATE Product SET CUserID = 11 WHERE SerialNumber = 'SN-SRV-101';

-- 1. Talep Oluþturma (Trigger stoklarý UnderRepair'e çeker)
INSERT INTO RepairRequest (SerialNumber, Status) VALUES ('SN-SRV-101', 'Accepted'); 
-- RequestID: 1

-- 2. Tamire Baþlama
INSERT INTO Repair (RequestID, StartDate, Response, TEUserID) VALUES
(1, GETDATE(), 'NOT COMPLETED', 5); -- Ali usta bakýyor

-- 3. Tamiri Bitirme (Trigger: Status Completed, Stok Field'a döner, EndDate atýlýr)
UPDATE Repair SET Response = 'COMPLETED' WHERE RepairID = 1;

-- Baþka bir Arýza (Devam Eden)
UPDATE Product SET CUserID = 17 WHERE SerialNumber = 'SN-STO-601'; -- Satýlmýþ varsayýyoruz
INSERT INTO RepairRequest (SerialNumber, Status) VALUES ('SN-STO-601', 'Accepted'); -- RequestID: 2
INSERT INTO Repair (RequestID, StartDate, Response, TEUserID) VALUES
(2, GETDATE(), 'NOT COMPLETED', 7); -- Ayse usta bakýyor

GO
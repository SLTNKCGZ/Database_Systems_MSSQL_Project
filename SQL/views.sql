CREATE VIEW vw_CommunityCompanyContacts
AS
SELECT
    cc.CompanyTradeName,
    LTRIM(RTRIM(
        ccom.FirstName + ' ' +
        ISNULL(ccom.MiddleName + ' ', '') +
        ccom.LastName
    )) AS Name,
    ccom.DepartmentName,
    ccom.MailAddress,
    ccom.TelCode + ccom.TelNo AS TelNo
FROM CustomerCompany cc
JOIN CommunityCompany ccom
    ON cc.CUserID = ccom.CUserID;


GO





CREATE VIEW vw_SalariedEmployee
AS
SELECT
    LTRIM(RTRIM(
        e.FirstName + ' ' +
        ISNULL(e.MiddleName + ' ', '') +
        e.LastName
    )) AS Name,
    e.TC,
    se.Salary,
    d.Name AS DepartmentName
FROM Employee e
JOIN SalariedEmployee se
    ON e.EUserID = se.EUserID
JOIN Department d
    ON se.DepartmentNo = d.DepartmentNo;


GO


CREATE VIEW vw_Technicians
AS
SELECT
    LTRIM(RTRIM(
        e.FirstName + ' ' +
        ISNULL(e.MiddleName + ' ', '')
    )) AS Name,
    e.TC,
    e.LastName AS Department,
    t.HourlySalary
FROM Employee e
JOIN Technician t
    ON e.EUserID = t.EUserID;

GO
Create view vw_EmployeesForEveryone
AS
SELECT 
    LTRIM(RTRIM(
        e.FirstName + ' ' +
        ISNULL(e.MiddleName + ' ', '') +
        e.LastName
    )) AS Name,
    d.Name AS Department,
    e.EmployeeType,
    m.FirstName + ' ' + m.LastName AS ManagerName
FROM Employee e
    LEFT JOIN SalariedEmployee se ON e.EUserID = se.EUserID
    LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
    LEFT JOIN Employee m ON se.MEUserID = m.EUserID
WHERE e.EmployeeType = 'Salaried'
ORDER BY e.FirstName, e.LastName
GO

CREATE VIEW vw_EmployeesForIK
AS
SELECT 
            e.TC,
            LTRIM(RTRIM(
                e.FirstName + ' ' +
                ISNULL(e.MiddleName + ' ', '') +
                e.LastName
            )) AS Name,
            d.Name AS Department,
            e.EmployeeType,
            se.Salary,
            m.FirstName + ' ' + m.LastName AS ManagerFirstName
        FROM Employee e
        LEFT JOIN SalariedEmployee se ON e.EUserID = se.EUserID
        LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
        LEFT JOIN Employee m ON se.MEUserID = m.EUserID
        ORDER BY e.FirstName, e.LastName

GO



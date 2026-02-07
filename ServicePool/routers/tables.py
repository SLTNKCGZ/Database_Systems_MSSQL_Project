from fastapi import APIRouter, Depends, HTTPException, Query, Body, Cookie, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import text
from typing import Annotated, Optional, Dict, Any, List
from database import SessionLocal
from starlette import status as http_status
from routers.auth import AUTH_TOKEN_COOKIE, get_user_from_cookie
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/api/tables",
    tags=["Tables"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

VIEW_DISPLAY_NAMES = {
    # Employee views - hepsi "Employee" altında birleşiyor
    "vw_SalariedEmployeesForEveryone": "Employee",
    "vw_TechniciansForEveryone": "Employee",
    "vw_SalariedEmployeesForIK": "Employee",
    "vw_TechnicianEmployeesForIK": "Employee",
    # Customer/Company views
    "vw_CommunityCompanyContacts": "Community Company",
    # Product views
    "vw_ServerProducts": "Products",
    "vw_StorageProducts": "Products",
    "vw_OtherProducts": "Products",
    # Inventory views
    "vw_ServerInventory": "Inventory",
    "vw_StorageInventory": "Inventory",
    "vw_OtherProductsInventory": "Inventory",
    # Offer/Order views
    "vw_OfferLineDetails": "Offer Lines",
    "vw_OfferSummary": "Offers",
    "vw_OrderSummary": "Orders",
    # Feedback/Repair views
    "vw_CustomerFeedback": "Feedback",
    "vw_RepairRequest": "Repairs",
    # Legacy views (backward compatibility)
    "vw_SalariedEmployee": "Salaried Employees",
    "vw_Technicians": "Technicians",
}

# Base views that everyone can see
BASE_VIEWS = [
    "vw_SalariedEmployeesForEveryone", 
    "vw_TechniciansForEveryone", 
    "vw_CommunityCompanyContacts",
    "vw_ServerProducts",
    "vw_StorageProducts",
    "vw_OtherProducts",
    "vw_ServerInventory",
    "vw_StorageInventory",
    "vw_OtherProductsInventory",
    "vw_OfferLineDetails",
    "vw_OfferSummary",
    "vw_OrderSummary",
    "vw_CustomerFeedback",
    "vw_RepairRequest"
]
# HR-only views (HR olanlar bunları görür, normal employee view'leri görmez)
HR_VIEWS = ["vw_SalariedEmployeesForIK", "vw_TechnicianEmployeesForIK"]



@router.get("/list")
async def get_table_list(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    user_type: Optional[str] = Query("employee")
):
    # Customer için sadece Order ve Offer view'lerini göster
    if user_type == "customer":
        try:
            user_info = get_user_from_cookie(auth_token)
            if not user_info or user_info.get('user_type') != 'customer':
                return {"tables": []}
            
            # Customer için sadece Order ve Offer view'lerini getir
            customer_views = ["vw_OrderSummary", "vw_OfferSummary"]
            views_query = text(f"""
                SELECT 
                    s.name AS schema_name,
                    v.name AS view_name,
                    QUOTENAME(s.name) + '.' + QUOTENAME(v.name) AS full_name
                FROM sys.views v
                JOIN sys.schemas s ON v.schema_id = s.schema_id
                WHERE v.is_ms_shipped = 0
                AND v.name IN ({",".join(f"'{v}'" for v in customer_views)})
                ORDER BY s.name, v.name
            """)
            
            views = db.execute(views_query).mappings().all()
            tables_list = []
            
            for v in views:
                view_name = v["view_name"]
                display_name = VIEW_DISPLAY_NAMES.get(view_name, view_name)
                tables_list.append({
                    "schema": v["schema_name"],
                    "table_name": view_name,
                    "full_name": v["full_name"],
                    "display_name": display_name
                })
            
            return {"tables": tables_list}
        except Exception as e:
            print(f"Error loading customer tables: {e}")
            return {"tables": []}
    
    # SADECE employee görsün
    if user_type != "employee":
        return {"tables": []}
    try:
        # HR kontrolü - kullanıcının İnsan Kaynakları departmanında olup olmadığını kontrol et
        is_hr = False
        user_id = None
        if auth_token:
            try:
                user_info = get_user_from_cookie(auth_token)
                if user_info:
                    user_id = user_info.get("id")

                if user_id:
                    q = text("""
                        SELECT d.Name
                        FROM Employee e
                        JOIN SalariedEmployee se ON e.EUserID = se.EUserID
                        JOIN Department d ON se.DepartmentNo = d.DepartmentNo
                        WHERE e.EUserID = :user_id
                    """)
                    row = db.execute(q, {"user_id": user_id}).scalar()
                    if row == "İnsan Kaynakları":
                        is_hr = True
            except:
                pass

        # Kullanıcı tipine göre gösterilecek view'leri belirle
        if is_hr:
            # İK ise: HR view'lerini göster, normal employee view'lerini gösterme
            allowed_views = BASE_VIEWS.copy()
            # Normal employee view'lerini kaldır
            allowed_views.remove("vw_SalariedEmployeesForEveryone")
            allowed_views.remove("vw_TechniciansForEveryone")
            # HR view'lerini ekle
            allowed_views.extend(HR_VIEWS)
        else:
            # Normal employee ise: sadece normal employee view'lerini göster
            allowed_views = BASE_VIEWS.copy()

        # VIEW'LERİ GETİR
        views_query = text(f"""
            SELECT 
                s.name AS schema_name,
                v.name AS view_name,
                QUOTENAME(s.name) + '.' + QUOTENAME(v.name) AS full_name
            FROM sys.views v
            JOIN sys.schemas s ON v.schema_id = s.schema_id
            WHERE v.is_ms_shipped = 0
            AND v.name IN ({",".join(f"'{v}'" for v in allowed_views)})
            ORDER BY s.name, v.name
        """)

        views = db.execute(views_query).mappings().all()

        # Employee, Inventory ve Products view'lerini tek bir entry olarak birleştir
        employee_views = []
        inventory_views = []
        product_views = []
        other_views = []
        
        for v in views:
            view_name = v["view_name"]
            display_name = VIEW_DISPLAY_NAMES.get(view_name, view_name)
            
            # Employee view'lerini ayır
            if display_name == "Employee":
                employee_views.append({
                    "schema": v["schema_name"],
                    "table_name": view_name,
                    "full_name": v["full_name"],
                    "display_name": display_name
                })
            # Inventory view'lerini ayır
            elif display_name == "Inventory":
                inventory_views.append({
                    "schema": v["schema_name"],
                    "table_name": view_name,
                    "full_name": v["full_name"],
                    "display_name": display_name
                })
            # Products view'lerini ayır
            elif display_name == "Products":
                product_views.append({
                    "schema": v["schema_name"],
                    "table_name": view_name,
                    "full_name": v["full_name"],
                    "display_name": display_name
                })
            else:
                other_views.append({
                    "schema": v["schema_name"],
                    "table_name": view_name,
                    "full_name": v["full_name"],
                    "display_name": display_name
                })
        
        # Employee view'leri varsa tek bir entry olarak ekle
        tables_list = []
        if employee_views:
            # HR ise HR view'lerini, değilse Everyone view'lerini kullan
            if is_hr:
                salaried_view = next((v for v in employee_views if "SalariedEmployeesForIK" in v["table_name"]), None)
                technician_view = next((v for v in employee_views if "TechnicianEmployeesForIK" in v["table_name"]), None)
            else:
                salaried_view = next((v for v in employee_views if "SalariedEmployeesForEveryone" in v["table_name"]), None)
                technician_view = next((v for v in employee_views if "TechniciansForEveryone" in v["table_name"]), None)
            
            # Özel Employee entry'si oluştur
            tables_list.append({
                "schema": "dbo",
                "table_name": "Employee",
                "full_name": "dbo.Employee",
                "display_name": "Employee",
                "type": "employee",
                "salaried_view": salaried_view,
                "technician_view": technician_view
            })
        
        # Inventory view'leri varsa tek bir entry olarak ekle
        if inventory_views:
            server_view = next((v for v in inventory_views if "ServerInventory" in v["table_name"]), None)
            storage_view = next((v for v in inventory_views if "StorageInventory" in v["table_name"]), None)
            
            # Özel Inventory entry'si oluştur
            tables_list.append({
                "schema": "dbo",
                "table_name": "Inventory",
                "full_name": "dbo.Inventory",
                "display_name": "Inventory",
                "type": "inventory",
                "server_view": server_view,
                "storage_view": storage_view
            })
        
        # Products view'leri varsa tek bir entry olarak ekle
        if product_views:
            server_view = next((v for v in product_views if "ServerProducts" in v["table_name"]), None)
            storage_view = next((v for v in product_views if "StorageProducts" in v["table_name"]), None)
            
            # Özel Products entry'si oluştur
            tables_list.append({
                "schema": "dbo",
                "table_name": "Products",
                "full_name": "dbo.Products",
                "display_name": "Products",
                "type": "products",
                "server_view": server_view,
                "storage_view": storage_view
            })
        
        # Diğer view'leri ekle
        tables_list.extend(other_views)
        
        return {"tables": tables_list}



    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/{schema}/{table_name}/data")
async def get_table_data(
    schema: str, 
    table_name: str, 
    db: db_dependency, 
    limit: int = 100, 
    offset: int = 0,
    search: Optional[str] = Query(None, description="Tablo içeriğinde arama yapmak için"),
    auth_token: Optional[str] = Cookie(None)
):
    """
    Get data from a specific table with schema
    Optional search parameter to filter table data
    Employee ve SalariedEmployee tabloları sadece İnsan Kaynakları departmanı için erişilebilir
    """
    try:
        # SQL injection koruması - alfanumerik, alt çizgi, tire ve nokta karakterlerine izin ver
        # Özel karakterleri temizleyip kontrol et
        schema_clean = schema.replace('_', '').replace('-', '').replace('.', '')
        table_name_clean = table_name.replace('_', '').replace('-', '').replace('.', '')
        if not schema_clean.isalnum() or not table_name_clean.isalnum():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid schema or table name"
            )
        
        full_table_name = f"{schema}.{table_name}"
        
        # Employee, SalariedEmployee, Technician ve E- ile başlayan tablolar için yetki kontrolü
        restricted_tables = ['Employee', 'SalariedEmployee', 'Technician']
        is_restricted = (table_name in restricted_tables) or (table_name.startswith('E-'))
        if is_restricted:
            if not auth_token:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Bu tabloya erişmek için yetkiniz yok"
                )
            
            # Kullanıcının departmanını kontrol et
            try:
                from jose import JWTError
                user_info = get_user_from_cookie(auth_token)
                if not user_info:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="Geçersiz token"
                    )
                user_id = user_info.get('id')
                
                if user_id:
                    # Employee bilgilerini al (Department SalariedEmployee tablosundan)
                    employee_query = text("""
                        SELECT d.Name AS Department
                        FROM Employee e
                        INNER JOIN SalariedEmployee se ON e.EUserID = se.EUserID
                        LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
                        WHERE e.EUserID = :user_id
                    """)
                    employee_data = db.execute(employee_query, {"user_id": user_id}).mappings().first()
                    if not employee_data or employee_data['Department'] != 'İnsan Kaynakları':
                        raise HTTPException(
                            status_code=http_status.HTTP_403_FORBIDDEN,
                            detail="Bu tabloya erişmek için yetkiniz yok. Sadece İnsan Kaynakları departmanı erişebilir."
                        )
                else:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="Bu tabloya erişmek için yetkiniz yok"
                    )
            except (JWTError, HTTPException):
                raise
            except Exception:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Geçersiz token"
                )
        
        # Önce tablo veya view var mı kontrol et
        check_table_query = text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
        """)
        check_view_query = text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.VIEWS 
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
        """)
        table_exists = db.execute(check_table_query, {"schema": schema, "table_name": table_name}).scalar()
        view_exists = db.execute(check_view_query, {"schema": schema, "table_name": table_name}).scalar()
        
        if not table_exists and not view_exists:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Table or View '{full_table_name}' not found"
            )
        
        # Tablo veya view kolonlarını al
        columns_query = text("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
        """)
        columns_result = db.execute(columns_query, {"schema": schema, "table_name": table_name})
        columns = [row[0] for row in columns_result.fetchall()]
        
        # View'ler için yetki kontrolü yapma (zaten list endpoint'inde kontrol edildi)
        
        # Arama parametresi varsa WHERE koşulu oluştur
        where_clause = ""
        search_params = {"offset": offset, "limit": limit}
        
        if search and search.strip():
            # Tüm kolonlarda arama yapmak için dinamik WHERE koşulu oluştur
            # Her kolon için CAST ile string'e çevirip LIKE ile arama yap
            search_conditions = []
            search_pattern = f"%{search}%"
            
            for i, col in enumerate(columns):
                # SQL injection koruması için kolon ismini QUOTENAME ile sarmalıyız
                search_conditions.append(f"CAST([{col}] AS NVARCHAR(MAX)) LIKE :search_pattern")
            
            if search_conditions:
                where_clause = "WHERE " + " OR ".join(search_conditions)
                search_params["search_pattern"] = search_pattern
        
        # Tablo verilerini al - schema ile birlikte
        data_query = text(f"""
            SELECT * FROM [{schema}].[{table_name}]
            {where_clause}
            ORDER BY (SELECT NULL)
            OFFSET :offset ROWS
            FETCH NEXT :limit ROWS ONLY
        """)
        
        result = db.execute(data_query, search_params)
        rows = result.mappings().all()
        
        # Toplam kayıt sayısı (arama varsa filtrelenmiş sayı)
        if search and search.strip():
            count_query = text(f"""
                SELECT COUNT(*) FROM [{schema}].[{table_name}]
                {where_clause}
            """)
            total_count = db.execute(count_query, {"search_pattern": search_pattern}).scalar()
        else:
            count_query = text(f"SELECT COUNT(*) FROM [{schema}].[{table_name}]")
            total_count = db.execute(count_query).scalar()
        
        return {
            "schema": schema,
            "table_name": table_name,
            "full_table_name": full_table_name,
            "columns": columns,
            "data": [dict(row) for row in rows],
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "search": search
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching table data: {str(e)}"
        )


class UpdateRecordRequest(BaseModel):
    old_data: Dict[str, Any]
    new_data: Dict[str, Any]


@router.post("/update/{schema}/{table_name}", tags=["Tables"])
async def update_table_record(
    schema: str,
    table_name: str,
    db: db_dependency,
    request_data: UpdateRecordRequest = Body(...),
    auth_token: Optional[str] = Cookie(None)
):
    """
    Update a record in a table
    Sadece İnsan Kaynakları departmanı restricted tablolarda güncelleme yapabilir
    View'ler güncellenemez (read-only)
    """
    try:
        from jose import JWTError
        
        old_data = request_data.old_data
        new_data = request_data.new_data
        
        # View'ler güncellenemez
        check_view_query = text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.VIEWS 
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
        """)
        is_view = db.execute(check_view_query, {"schema": schema, "table_name": table_name}).scalar() > 0
        
        if is_view:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="View'ler güncellenemez. Güncelleme için doğrudan tabloları kullanın."
            )
        
        # Restricted tablolar için yetki kontrolü
        restricted_tables = ['Employee', 'SalariedEmployee', 'Technician']
        is_restricted = (table_name in restricted_tables) or (table_name.startswith('E-'))
        
        if is_restricted:
            if not auth_token:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Bu tabloda güncelleme yapmak için authentication gerekli"
                )
            
            user_info = get_user_from_cookie(auth_token)
            if not user_info:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Geçersiz token"
                )
            user_id = user_info.get('id')
            
            if user_id:
                # Employee bilgilerini al
                salaried_check = text("""
                    SELECT COUNT(*) as cnt
                    FROM SalariedEmployee
                    WHERE EUserID = :user_id
                """)
                salaried_exists = db.execute(salaried_check, {"user_id": user_id}).scalar()
                
                if salaried_exists > 0:
                    employee_query = text("""
                        SELECT d.Name AS Department
                        FROM Employee e
                        INNER JOIN SalariedEmployee se ON e.EUserID = se.EUserID
                        LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
                        WHERE e.EUserID = :user_id
                    """)
                    employee_data = db.execute(employee_query, {"user_id": user_id}).mappings().first()
                    department = employee_data['Department'] if employee_data else None
                    
                    if not employee_data or employee_data['Department'] != 'İnsan Kaynakları':
                        raise HTTPException(
                            status_code=http_status.HTTP_403_FORBIDDEN,
                            detail=f"Bu tabloda güncelleme yapmak için yetkiniz yok. Sadece İnsan Kaynakları departmanı güncelleme yapabilir. (Mevcut departman: {department})"
                        )
                else:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="Bu tabloda güncelleme yapmak için yetkiniz yok. Kullanıcı SalariedEmployee tablosunda bulunamadı."
                    )
            else:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Geçersiz token - user_id bulunamadı"
                )
        
        # SQL injection koruması - sadece tehlikeli karakterleri kontrol et
        # Schema ve table name'de tehlikeli SQL komutlarını kontrol et
        dangerous_patterns = [';', '--', '/*', '*/', 'xp_', 'sp_', 'exec', 'execute', 'union', 'drop', 'delete', 'truncate']
        schema_lower = schema.lower()
        table_name_lower = table_name.lower()
        for pattern in dangerous_patterns:
            if pattern in schema_lower or pattern in table_name_lower:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid schema or table name"
                )
        
        # Tablo kolonlarını ve tiplerini al
        columns_query = text("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
        """)
        columns_result = db.execute(columns_query, {"schema": schema, "table_name": table_name})
        columns_data = columns_result.mappings().all()
        columns = [row['COLUMN_NAME'] for row in columns_data]
        # Kolon tiplerini dictionary olarak sakla
        column_types = {row['COLUMN_NAME']: row['DATA_TYPE'] for row in columns_data}
        
        if not columns:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )
        
        # Gerçek primary key'i bul
        primary_key_query = text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = :schema 
            AND TABLE_NAME = :table_name
            AND OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
        """)
        pk_result = db.execute(primary_key_query, {"schema": schema, "table_name": table_name})
        pk_row = pk_result.fetchone()
        
        # Primary key bulunamazsa ilk kolonu kullan
        if pk_row:
            primary_key = pk_row[0]
        else:
            primary_key = columns[0]
        
        primary_key_value = old_data.get(primary_key)
        
        if primary_key_value is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Primary key value not found for column: {primary_key}"
            )
        
        # View'lerden güncelleme yapılıyorsa, altındaki tabloya güncelleme yap
        # Employee view'leri için özel işlem
        is_employee_view = table_name.startswith('vw_') and ('SalariedEmployees' in table_name or 'Technician' in table_name)
        
        if is_employee_view:
            # View'den tabloya çevir
            if 'SalariedEmployees' in table_name:
                target_table = 'SalariedEmployee'
                salary_col = 'Salary'
            elif 'Technician' in table_name:
                target_table = 'Technician'
                salary_col = 'HourlySalary'
            else:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid employee view for update"
                )
            
            # TC'den EUserID'ye çevir
            employee_id = None
            if 'TC' in old_data:
                tc_value = old_data['TC']
                emp_query = text("SELECT EUserID FROM Employee WHERE TC = :tc")
                emp_result = db.execute(emp_query, {"tc": tc_value}).fetchone()
                if emp_result:
                    employee_id = emp_result[0]
                else:
                    raise HTTPException(
                        status_code=http_status.HTTP_404_NOT_FOUND,
                        detail=f"Employee with TC {tc_value} not found"
                    )
            else:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="TC (Turkish ID) is required for employee view updates"
                )
            
            # Salary, Department ve Manager kolonlarını güncelle
            set_clauses = []
            update_params = {}
            
            # Salary kolonunu bul (Salary veya HourlySalary) - opsiyonel
            salary_value = None
            for col in new_data.keys():
                if col.lower() in ['salary', 'hourlysalary']:
                    salary_value = new_data[col]
                    break
            
            if salary_value is not None:
                set_clauses.append(f"[{salary_col}] = :salary")
                if salary_value == '' or salary_value is None:
                    update_params['salary'] = None
                else:
                    try:
                        update_params['salary'] = float(salary_value)
                    except (ValueError, TypeError):
                        raise HTTPException(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid salary value: {salary_value}"
                        )
            
            # Department kolonunu bul (sadece kadrolu çalışanlar için) - opsiyonel
            if 'SalariedEmployees' in table_name:
                department_value = None
                for col in new_data.keys():
                    if col.lower() in ['department', 'departmentname']:
                        department_value = new_data[col]
                        break
                
                if department_value is not None:
                    # DepartmentName'den DepartmentNo'ya çevir
                    if department_value == '' or department_value is None:
                        # NULL departman
                        set_clauses.append("[DepartmentNo] = :department_no")
                        update_params['department_no'] = None
                    else:
                        dept_query = text("SELECT DepartmentNo FROM Department WHERE Name = :dept_name")
                        dept_result = db.execute(dept_query, {"dept_name": department_value}).fetchone()
                        if dept_result:
                            dept_no = dept_result[0]
                            set_clauses.append("[DepartmentNo] = :department_no")
                            update_params['department_no'] = dept_no
                        else:
                            raise HTTPException(
                                status_code=http_status.HTTP_404_NOT_FOUND,
                                detail=f"Department '{department_value}' not found"
                            )
            
            if not set_clauses:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update. Please update at least one field (Salary, Department, or Manager)."
                )
            
            # UPDATE sorgusu
            update_query = text(f"""
                UPDATE [dbo].[{target_table}]
                SET {', '.join(set_clauses)}
                WHERE EUserID = :employee_id
            """)
            update_params['employee_id'] = employee_id
        else:
            # Normal tablo güncelleme
            set_clauses = []
            update_params = {}
            
            for col in columns:
                if col in new_data and col != primary_key:  # Primary key'i güncelleme
                    # Kolon adını güvenli hale getir
                    set_clauses.append(f"[{col}] = :{col}")
                    
                    # Değeri parametre olarak ekle
                    val = new_data[col]
                    
                    # NULL değerleri None olarak işle
                    if val == '' or val is None:
                        update_params[col] = None
                    else:
                        # Date/datetime tiplerini kontrol et ve dönüştür
                        col_type = column_types.get(col, '').upper()
                        if col_type in ('DATE', 'DATETIME', 'DATETIME2', 'SMALLDATETIME', 'DATETIMEOFFSET'):
                            # Date string'ini datetime objesine çevir
                            try:
                                from datetime import datetime
                                if isinstance(val, str):
                                    # YYYY-MM-DD formatını parse et
                                    date_obj = datetime.strptime(val, "%Y-%m-%d")
                                    update_params[col] = date_obj
                                else:
                                    update_params[col] = val
                            except ValueError as e:
                                raise HTTPException(
                                    status_code=http_status.HTTP_400_BAD_REQUEST,
                                    detail=f"Invalid date format for column {col}: {val}. Expected YYYY-MM-DD format."
                                )
                        else:
                            update_params[col] = val
            
            if not set_clauses:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            # UPDATE sorgusu - köşeli parantezlerle güvenli hale getir
            update_query = text(f"""
                UPDATE [{schema}].[{table_name}]
                SET {', '.join(set_clauses)}
                WHERE [{primary_key}] = :primary_key_value
            """)
            update_params['primary_key_value'] = primary_key_value
        
        result = db.execute(update_query, update_params)
        rows_affected = result.rowcount
        db.commit()
        
        if rows_affected == 0:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"No record found to update with {primary_key} = {primary_key_value}"
            )
        
        return {"status": "success", "message": "Record updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating record: {str(e)}"
        )


# Offer oluşturma için Pydantic modelleri
class OfferLineCreate(BaseModel):
    product_code: str
    quantity: int
    sales_unit_price: float
    purchase_total_price: Optional[float] = None


@router.post("/offers/create-step1", tags=["Tables"])
async def create_offer_step1(
    db: db_dependency,
    customer_id: int = Form(...),
    exchange_rate: float = Form(...),
    payment_term: str = Form(...),
    term: str = Form(...),
    auth_token: Optional[str] = Cookie(None)
):
    """
    ADIM 1: Sadece temel Offer bilgilerini oluştur (derived alanlar null)
    Date ve Status otomatik olarak varsayılan değerlerle ayarlanır
    """
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # Zorunlu alanları kontrol et
        if not customer_id:
            raise HTTPException(status_code=400, detail="Müşteri seçimi zorunludur")
        if not exchange_rate or exchange_rate <= 0:
            raise HTTPException(status_code=400, detail="Döviz kuru zorunludur ve 0'dan büyük olmalıdır")
        if not payment_term:
            raise HTTPException(status_code=400, detail="Ödeme vadesi zorunludur")
        if not term:
            raise HTTPException(status_code=400, detail="Vade açıklaması zorunludur")
        
        # Müşteriyi kontrol et
        customer_check = text("SELECT CUserID FROM CustomerCompany WHERE CUserID = :customer_id")
        customer_exists = db.execute(customer_check, {"customer_id": customer_id}).scalar()
        if not customer_exists:
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı")
        
        # Tarih bugünü kullan (default GETDATE() kullanılacak)
        offer_date = datetime.now()
        payment_term_date = datetime.strptime(payment_term, "%Y-%m-%d").date()
        # Status varsayılan olarak "NotAccepted" (default değer)
        status = "NotAccepted"
        
        # Offer oluştur (Date ve Status default değerlerle, SalesAmountUSD, PurchaseAmountUSD null olarak - trigger'lar güncelleyecek)
        create_offer_query = text("""
            INSERT INTO Offer (CUserID, ExchangeRate, PaymentTerm, Term)
            OUTPUT INSERTED.OfferNo
            VALUES (:customer_id, :exchange_rate, :payment_term, :term)
        """)
        result = db.execute(create_offer_query, {
            "customer_id": customer_id,
            "exchange_rate": exchange_rate,
            "payment_term": payment_term_date,
            "term": term
        })
        offer_no = result.scalar()
        
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Teklif oluşturuldu",
            "offer_no": offer_no
        })
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Tarih formatı hatalı: {str(e)}")
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


@router.post("/offers/{offer_no}/offerlines", tags=["Tables"])
async def add_offer_line(
    offer_no: int,
    db: db_dependency,
    product_code: str = Form(...),
    quantity: int = Form(...),
    sales_unit_price: float = Form(...),
    auth_token: Optional[str] = Cookie(None)
):
    """
    ADIM 2: OfferLine ekle (trigger/procedure otomatik olarak Offer'ı güncelleyecek)
    """
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # Zorunlu alanları kontrol et
        if not product_code:
            raise HTTPException(status_code=400, detail="Ürün kodu zorunludur")
        if not quantity or quantity < 1:
            raise HTTPException(status_code=400, detail="Miktar zorunludur ve 1'den büyük olmalıdır")
        if not sales_unit_price or sales_unit_price <= 0:
            raise HTTPException(status_code=400, detail="Birim fiyat zorunludur ve 0'dan büyük olmalıdır")
        
        # Offer'ı kontrol et
        offer_check = text("SELECT OfferNo FROM Offer WHERE OfferNo = :offer_no")
        offer_exists = db.execute(offer_check, {"offer_no": offer_no}).scalar()
        if not offer_exists:
            raise HTTPException(status_code=404, detail="Teklif bulunamadı")
        
        # Ürünü kontrol et
        product_check = text("SELECT ProductCode FROM ProductInventory WHERE ProductCode = :product_code")
        product_exists = db.execute(product_check, {"product_code": product_code}).scalar()
        if not product_exists:
            raise HTTPException(status_code=404, detail=f"Ürün bulunamadı: {product_code}")
        
        # OfferLine oluştur
        # Mevcut trigger (trg_OfferLine_Management) otomatik olarak:
        # - PurchaseTotalPrice = Quantity * PurchaseUnitPrice (ProductInventory'den) hesaplayacak
        # - LineItemProfitability hesaplayacak
        # - Offer'daki SalesAmountUSD, PurchaseAmountUSD, ProfitUSD, ProfitPercent'i güncelleyecek
        create_offer_line_query = text("""
            INSERT INTO OfferLine (OfferNo, ProductCode, Quantity, SalesUnitPrice)
            VALUES (:offer_no, :product_code, :quantity, :sales_unit_price)
        """)
        db.execute(create_offer_line_query, {
            "offer_no": offer_no,
            "product_code": product_code,
            "quantity": quantity,
            "sales_unit_price": sales_unit_price
        })
        
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Ürün eklendi"
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


@router.get("/offers/customers", tags=["Tables"])
async def get_customers(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Müşteri listesini getir"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        customers_query = text("""
            SELECT CUserID, CompanyTradeName
            FROM CustomerCompany
            ORDER BY CompanyTradeName
        """)
        customers = db.execute(customers_query).mappings().all()
        
        return JSONResponse({
            "customers": [{"id": row['CUserID'], "name": row['CompanyTradeName']} for row in customers]
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


@router.get("/offers/products", tags=["Tables"])
async def get_products(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Ürün listesini getir"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        products_query = text("""
            SELECT ProductCode, ProductDescription
            FROM ProductInventory
            ORDER BY ProductCode
        """)
        products = db.execute(products_query).mappings().all()
        
        return JSONResponse({
            "products": [{"code": row['ProductCode'], "description": row['ProductDescription']} for row in products]
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException, Request, Form, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from starlette import status as http_status
from database import SessionLocal
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set. Please create a .env file with SECRET_KEY.")
ALGORITHM = "HS256"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

# Cookie name for authentication token
AUTH_TOKEN_COOKIE = "auth_token"


def create_access_token(identifier: str, user_id: int, user_type: str, expires_delta: timedelta):
    payload = {'sub': identifier, 'id': user_id, 'user_type': user_type}
    expires = datetime.now(timezone.utc) + expires_delta
    payload.update({'exp': expires})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(identifier: str, password: str, role: str, db: Session):
    """
    Authenticate user based on role using SQL queries:
    - employee: uses TC (11 digits) as identifier
    - customer: uses Trade Registry Number as identifier
    """
    try:
        if role == "employee":
            from queries import AUTH
            employee_query = text(AUTH["authenticate_employee"])

            result = db.execute(employee_query, {"tc": identifier})
            employee_data = result.mappings().first()
            
            if not employee_data:
                return None
            
            stored_password = employee_data['Password']
            if not stored_password or stored_password != password:
                return None
            
            return {
                'user_id': employee_data['UserID'],
                'employee_id': employee_data['EUserID'],
                'user_type': 'employee',
                'identifier': employee_data['TC'],
                'first_name': employee_data['FirstName'],
                'last_name': employee_data['LastName']
            }
        
        elif role == "customer":
            from queries import AUTH
            customer_query = text(AUTH["authenticate_customer"])
            result = db.execute(customer_query, {"registry_no": identifier})
            customer_data = result.mappings().first()
            
            if not customer_data:
                return None
            
            stored_password = customer_data['Password']
            if not stored_password or stored_password != password:
                return None
            
            return {
                'user_id': customer_data['UserID'],
                'customer_id': customer_data['CUserID'],
                'user_type': 'customer',
                'identifier': customer_data['TradeRegistryNumber'],
                'company_name': customer_data['CompanyTradeName']
            }
        
        return None
    except Exception as e:
        print(f"Authentication error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_user_from_cookie(auth_token: Optional[str] = Cookie(None)):
    """
    Cookie'den token'ı al ve kullanıcı bilgilerini döndür
    """
    if not auth_token:
        return None
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier = payload.get('sub')
        user_id = payload.get('id')
        user_type = payload.get('user_type')
        if identifier is None or user_id is None:
            return None
        return {'identifier': identifier, 'id': user_id, 'user_type': user_type}
    except JWTError:
        return None


# --- LOGIN ENDPOINTS ---
@router.get("/login", response_class=HTMLResponse, tags=["Authentication"])
async def get_login(request: Request, role: str = "employee"):
    """
    Login page for Employee or Customer
    """
    return templates.TemplateResponse("login.html", {"request": request, "role": role})


@router.post("/login", tags=["Authentication"])
async def handle_login(
    db: db_dependency,
    identifier: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    """
    Login endpoint for both Employee and Customer
    
    - **Employee**: identifier is TC (11 digits)
    - **Customer**: identifier is Trade Registry Number
    
    Sets authentication token in HTTP-only cookie and redirects to dashboard.
    """
    auth_result = authenticate_user(identifier, password, role, db)
    
    if not auth_result:
        return RedirectResponse(
            url=f"/auth/login?error=invalid_credentials&role={role}",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
    
    # Token oluştur
    token = create_access_token(
        auth_result['identifier'],
        auth_result['user_id'],
        auth_result['user_type'],
        timedelta(days=30)
    )
    
    # Cookie'ye token'ı set et (HttpOnly, Secure, SameSite)
    response = RedirectResponse(
        url="/dashboard",
        status_code=http_status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(
        key=AUTH_TOKEN_COOKIE,
        value=token,
        max_age=30 * 24 * 60 * 60,  # 30 gün
        httponly=True,
        secure=False,  # HTTPS kullanıyorsanız True yapın
        samesite="lax"
    )
    
    return response


# --- REGISTER ENDPOINTS ---
@router.get("/departments", response_class=JSONResponse, tags=["Authentication"])
async def get_departments(db: db_dependency):
    """
    Get list of all departments from Department table
    """
    try:
        query = text("""
            SELECT DepartmentNo, Name 
            FROM [Department] 
            WHERE Name IS NOT NULL
            ORDER BY DepartmentNo
        """)
        result = db.execute(query)
        departments = result.mappings().all()
        
        return JSONResponse({
            "departments": [
                {
                    "id": row['DepartmentNo'],
                    "name": row['Name']
                }
                for row in departments
            ]
        })
    except Exception as e:
        print(f"ERROR fetching departments: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"departments": []})


@router.get("/register", response_class=HTMLResponse, tags=["Authentication"])
async def get_register(request: Request, role: str = "employee"):
    """
    Registration page for Employee or Customer
    """
    return templates.TemplateResponse("register.html", {"request": request, "role": role})


@router.post("/register", tags=["Authentication"])
async def handle_register(
    db: db_dependency,
    role: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    employee_type: str = Form(...),
    tc: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    middle_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    hired_date: Optional[str] = Form(None),
    registry_no: Optional[str] = Form(None),
    company_trade_name: Optional[str] = Form(None),
    tax_office: Optional[str] = Form(None),
    tax_number: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    year_of_establishment: Optional[int] = Form(None),
):
    """
    Register endpoint for both Employee and Customer using SQL queries
    
    - **Employee**: Requires TC, FirstName, LastName, BirthDate, HiredDate
    - **Customer**: Requires TradeRegistryNumber, CompanyTradeName, TaxOffice, TaxNumber
    
    Returns redirect to login page on success.
    """
    # Password confirmation check
    if password != confirm_password:
        return RedirectResponse(
            url=f"/auth/register?error=password_mismatch&role={role}",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
    
    try:
        if role == "employee":
            if not all([tc, first_name, last_name, department, birth_date, hired_date]):
                return RedirectResponse(
                    url="/auth/register?error=missing_fields&role=employee",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            
            if len(tc) != 11 or not tc.isdigit():
                return RedirectResponse(
                    url="/auth/register?error=invalid_tc&role=employee",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            
            check_tc_query = text("SELECT EUserID FROM Employee WHERE TC = :tc")
            existing = db.execute(check_tc_query, {"tc": tc}).mappings().first()
            if existing:
                return RedirectResponse(
                    url="/auth/register?error=tc_exists&role=employee",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            
            try:
                birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
                hired_date_obj = datetime.strptime(hired_date, "%Y-%m-%d")
            except ValueError:
                return RedirectResponse(
                    url="/auth/register?error=invalid_date&role=employee",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            try:
                sql_query = text("""
                    EXEC sp_RegisterSalariedEmployee 
                        @Password = :password,
                        @TC = :tc,
                        @FirstName = :first_name,
                        @MiddleName = :middle_name,
                        @LastName = :last_name,
                        @BirthDate = :birth_date,
                        @HiredDate = :hired_date,
                        @DepartmentName = :department_name
                """)
            
                result = db.execute(sql_query, {
                    "password": password,
                    "tc": tc,
                    "first_name": first_name,
                    "middle_name": middle_name if middle_name else None,
                    "last_name": last_name,
                    "birth_date": birth_date_obj,
                    "hired_date": hired_date_obj,
                    "department_name": department if department else None
                })
                        
                db.commit()
                
            except Exception as e:
                db.rollback()
                import traceback
                traceback.print_exc()
                print(f"Employee registration error: {e}")
                return RedirectResponse(
                    url="/auth/register?error=server_error&role=employee",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            
            return RedirectResponse(
                url=f"/auth/login?role=employee&success=registered",
                status_code=http_status.HTTP_303_SEE_OTHER
            )
        
        elif role == "customer":
            if not all([registry_no, company_trade_name, tax_office, tax_number]):
                return RedirectResponse(
                    url="/auth/register?error=missing_fields&role=customer",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            
            check_registry_query = text("SELECT CUserID FROM CustomerCompany WHERE TradeRegistryNumber = :registry_no")
            existing = db.execute(check_registry_query, {"registry_no": registry_no}).mappings().first()
            if existing:
                return RedirectResponse(
                    url="/auth/register?error=registry_exists&role=customer",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            try:
                sql_query = text("""
                    EXEC sp_RegisterCustomerCompany 
                        @Password = :password,
                        @TradeRegistryNumber = :registry_no,
                        @CompanyTradeName = :company_trade_name,
                        @Website = :website,
                        @YearOfEstablishment = :year_of_establishment,
                        @TaxOffice = :tax_office,
                        @TaxNumber = :tax_number
                """)
            
                result = db.execute(sql_query, {
                    "password": password,
                    "registry_no": registry_no,
                    "company_trade_name": company_trade_name,
                    "website": website if website else None,
                    "year_of_establishment": year_of_establishment if year_of_establishment else None,
                    "tax_office": tax_office,
                    "tax_number": tax_number
                })
                
                db.commit()
            
            except Exception as e:
                db.rollback()
                import traceback
                traceback.print_exc()
                print(f"Customer registration error: {e}")
                return RedirectResponse(
                    url="/auth/register?error=server_error&role=customer",
                    status_code=http_status.HTTP_303_SEE_OTHER
                )
            
            return RedirectResponse(
                url=f"/auth/login?role=customer&success=registered",
                status_code=http_status.HTTP_303_SEE_OTHER
            )
        
        else:
            return RedirectResponse(
                url="/auth/register?error=invalid_role",
                status_code=http_status.HTTP_303_SEE_OTHER
            )
    
    except Exception as e:
        db.rollback()
        print(f"Registration error: {e}")
        return RedirectResponse(
            url=f"/auth/register?error=server_error&role={role}",
            status_code=http_status.HTTP_303_SEE_OTHER
        )


@router.get("/logout", tags=["Authentication"])
@router.post("/logout", tags=["Authentication"])
async def handle_logout():
    """
    Logout endpoint - clears authentication cookie
    """
    response = RedirectResponse(
        url="/auth/login?role=employee",
        status_code=http_status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(
        key=AUTH_TOKEN_COOKIE,
        path="/",
        samesite="lax"
    )
    return response

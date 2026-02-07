from fastapi import APIRouter, Depends, HTTPException, Form, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated, Optional
from database import SessionLocal
from starlette import status as http_status
from routers.auth import get_user_from_cookie

router = APIRouter(
    prefix="/hr",
    tags=["Employee Management"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def get_user_id_from_cookie(auth_token: Optional[str] = Cookie(None)):
    """
    Cookie'den token'ı al ve user_id döndür
    """
    user_info = get_user_from_cookie(auth_token)
    if not user_info:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_info['id']


@router.get("/check-department", tags=["Employee Management"])
async def check_department(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """
    Kullanıcının departmanını kontrol et
    """
    try:
        user_id = get_user_id_from_cookie(auth_token)
        
        # Employee bilgilerini al (Department SalariedEmployee tablosundan)
        employee_query = text("""
            SELECT d.Name AS Department
            FROM Employee e
            INNER JOIN SalariedEmployee se ON e.EUserID = se.EUserID
            LEFT JOIN Department d ON se.DepartmentNo = d.DepartmentNo
            WHERE e.EUserID = :user_id
        """)
        employee_data = db.execute(employee_query, {"user_id": user_id}).mappings().first()
        
        if employee_data and employee_data['Department'] == 'İnsan Kaynakları':
            return {"is_hr": True, "department": employee_data['Department']}
        else:
            return {"is_hr": False, "department": employee_data['Department'] if employee_data else None}
    except Exception as e:
        return {"is_hr": False, "department": None, "error": str(e)}


def check_hr_permission(user_id: int, db: Session):
    """
    Kullanıcının İK yetkisi olup olmadığını kontrol et
    """
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
            detail="Bu işlem için yetkiniz yok. Sadece İnsan Kaynakları departmanı bu işlemi yapabilir."
        )
    return True


@router.post("/update-salary", tags=["Employee Management"])
async def update_salary(
    db: db_dependency,
    employee_id: int = Form(...),
    salary: Optional[float] = Form(None),
    auth_token: Optional[str] = Cookie(None)
):
    """
    Employee salary güncelleme - Sadece İK yetkisi olanlar yapabilir
    """
    # Cookie'den user_id al ve İK yetkisini kontrol et
    user_id = get_user_id_from_cookie(auth_token)
    check_hr_permission(user_id, db)
    
    # Salary güncelle
    update_query = text("""
        UPDATE SalariedEmployee
        SET Salary = :salary
        WHERE EUserID = :employee_id
    """)
    db.execute(update_query, {
        "salary": salary if salary else None,
        "employee_id": employee_id
    })
    db.commit()
    
    # Dashboard'a geri dön (view'den güncelleme yapıldığı için)
    return RedirectResponse(
        url="/dashboard?success=salary_updated",
        status_code=http_status.HTTP_303_SEE_OTHER
    )


@router.post("/assign-manager", tags=["Employee Management"])
async def assign_manager(
    db: db_dependency,
    employee_id: int = Form(...),
    manager_id: Optional[int] = Form(None),
    auth_token: Optional[str] = Cookie(None)
):
    """
    Employee'ye manager atama - Sadece İK yetkisi olanlar yapabilir
    """
    # Cookie'den user_id al ve İK yetkisini kontrol et
    user_id = get_user_id_from_cookie(auth_token)
    check_hr_permission(user_id, db)
    
    # Manager atama (MEUserID kullan)
    update_query = text("""
        UPDATE SalariedEmployee
        SET MEUserID = :manager_id
        WHERE EUserID = :employee_id
    """)
    db.execute(update_query, {
        "manager_id": manager_id if manager_id else None,
        "employee_id": employee_id
    })
    db.commit()
    
    # Dashboard'a geri dön (view'den güncelleme yapıldığı için)
    return RedirectResponse(
        url="/dashboard?success=manager_assigned",
        status_code=http_status.HTTP_303_SEE_OTHER
    )


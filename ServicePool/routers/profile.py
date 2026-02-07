from fastapi import APIRouter, Depends, HTTPException, Request, Form, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated, Optional
from database import SessionLocal
from starlette import status as http_status
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from routers.auth import SECRET_KEY, AUTH_TOKEN_COOKIE, get_user_from_cookie
from queries import PROFILE
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)

templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def get_customer_id(db: Session, user_id: int):
    """User ID'den Customer ID'yi bul"""
    query = text("SELECT CUserID FROM CustomerCompany WHERE CUserID = :user_id")
    result = db.execute(query, {"user_id": user_id}).scalar()
    return result


def get_user_info_from_cookie(auth_token: Optional[str] = Cookie(None)):
    """
    Cookie'den token'ı al ve kullanıcı bilgilerini döndür
    """
    user_info = get_user_from_cookie(auth_token)
    if not user_info:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_info['id'], user_info.get('user_type', 'employee')


@router.get("", response_class=HTMLResponse, tags=["Profile"])
async def get_profile_page(
    request: Request,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """
    Kullanıcının profil sayfası
    """
    try:
        try:
            user_id, user_type = get_user_info_from_cookie(auth_token)
        except HTTPException as e:
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "error": e.detail
            })
        
        # Employee ise Employee, SalariedEmployee, E-TelNo, E-MailAdress bilgilerini al
        if user_type == 'employee' or user_type == 'Employee':
            # Employee bilgileri
            employee_query = text(PROFILE["get_employee"])
            employee_result = db.execute(employee_query, {"user_id": user_id})
            employee_data = employee_result.mappings().first()
            
            # SalariedEmployee bilgileri
            salaried_query = text(PROFILE["get_salaried_employee"])
            salaried_result = db.execute(salaried_query, {"user_id": user_id})
            salaried_data = salaried_result.mappings().first()
            
            # E-TelNo bilgileri (TelCode ve TelNo birleştirilmiş)
            telno_query = text(PROFILE["get_employee_telno"])
            telno_result = db.execute(telno_query, {"user_id": user_id})
            telno_data = telno_result.mappings().all()
            # TelCode ve TelNo'yu birlikte sakla (silme işlemi için gerekli)
            tel_numbers = [{'telcode': row.get('TelCode', ''), 'telno': row.get('TelNo', ''), 'fulltelno': row['FullTelNo'] or row.get('TelNo', '')} for row in telno_data if row.get('FullTelNo') or row.get('TelNo')] if telno_data else []
            
            # E-MailAdress bilgileri - önce kolon adını bul
            try:
                # Tablo kolonlarını kontrol et
                columns_query = text(PROFILE["get_email_columns"])
                columns_result = db.execute(columns_query)
                email_columns = [row[0] for row in columns_result.fetchall()]
                
                # Email kolonunu bul (EmailAdress, Email, E-MailAdress vb.)
                email_column = None
                for col in email_columns:
                    if 'email' in col.lower() or 'mail' in col.lower():
                        email_column = col
                        break
                
                if email_column:
                    email_query = text(PROFILE["get_employee_emails"].replace("{email_column}", email_column))
                    email_result = db.execute(email_query, {"user_id": user_id})
                    email_data = email_result.mappings().all()
                    email_addresses = [row[email_column] for row in email_data] if email_data else []
                else:
                    # Kolon bulunamadı, boş liste döndür
                    email_addresses = []
            except Exception as e:
                email_addresses = []
            
            # User bilgileri (password hariç)
            user_query = text(PROFILE["get_user"])
            user_result = db.execute(user_query, {"user_id": user_id})
            user_data = user_result.mappings().first()
            
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user_id": user_id,
                "user_type": user_type,
                "employee": dict(employee_data) if employee_data else None,
                "salaried": dict(salaried_data) if salaried_data else None,
                "tel_numbers": tel_numbers,
                "email_addresses": email_addresses,
                "user": dict(user_data) if user_data else None,
                "token": auth_token
            })
        else:
            # Customer için bilgileri al
            customer_query = text(PROFILE["get_customer"])
            customer_result = db.execute(customer_query, {"user_id": user_id})
            customer_data = customer_result.mappings().first()
            
            # Customer iletişim kişileri (CommunityCompany tablosundan)
            try:
                customer_contacts_query = text(PROFILE["get_customer_contacts"])
                customer_contacts_result = db.execute(customer_contacts_query, {"user_id": user_id})
                customer_contacts_data = customer_contacts_result.mappings().all()
                # Tüm iletişim kişilerini sakla
                customer_contacts = [dict(row) for row in customer_contacts_data] if customer_contacts_data else []
            except Exception as e:
                customer_contacts = []
            
            # User bilgileri
            user_query = text("""
                SELECT UserID, RegisterDate, UserType
                FROM [User]
                WHERE UserID = :user_id
            """)
            user_result = db.execute(user_query, {"user_id": user_id})
            user_data = user_result.mappings().first()
            
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user_id": user_id,
                "user_type": user_type,
                "customer": dict(customer_data) if customer_data else None,
                "customer_contacts": customer_contacts,
                "user": dict(user_data) if user_data else None,
                "token": auth_token
            })
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Hata durumunda da HTML sayfası döndür (hata mesajı ile)
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "error": str(e)
        })


@router.post("/update-employee", tags=["Profile"])
async def update_employee_profile(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    first_name: Optional[str] = Form(None),
    middle_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
):
    """
    Employee profil bilgilerini güncelle
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'employee':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only employees can update employee profile"
            )
        
        # Güncelleme sorgusu
        update_fields = []
        update_params = {"user_id": user_id}
        
        if first_name:
            update_fields.append("FirstName = :first_name")
            update_params["first_name"] = first_name
        
        if middle_name is not None:
            update_fields.append("MiddleName = :middle_name")
            update_params["middle_name"] = middle_name if middle_name else None
        
        if last_name:
            update_fields.append("LastName = :last_name")
            update_params["last_name"] = last_name
        
        if birth_date:
            birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
            update_fields.append("BirthDate = :birth_date")
            update_params["birth_date"] = birth_date_obj
        
        if update_fields:
            update_query = text(PROFILE["update_employee"].replace("{update_fields}", ', '.join(update_fields)))
            db.execute(update_query, update_params)
            db.commit()
        
        return RedirectResponse(
            url="/profile?success=employee_updated",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating employee profile: {str(e)}"
        )


@router.post("/add-telno", tags=["Profile"])
async def add_telno(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    telno: str = Form(...),
    telcode: Optional[str] = Form(None),
):
    """
    Yeni telefon numarası ekle
    E-TelNo tablosu (EUserID, TelCode, TelNo) composite primary key kullanıyor
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'employee':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only employees can add phone numbers"
            )
        
        # TelCode yoksa varsayılan olarak +90 kullan (Türkiye)
        if not telcode:
            telcode = '+90'
        
        # Telefon numarası ekle (TelCode ve TelNo ile)
        insert_query = text(PROFILE["add_employee_telno"])
        db.execute(insert_query, {"user_id": user_id, "telcode": telcode, "telno": telno})
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=telno_added",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding phone number: {str(e)}"
        )


@router.post("/delete-telno", tags=["Profile"])
async def delete_telno(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    telno: str = Form(...),
    telcode: Optional[str] = Form(None),
):
    """
    Telefon numarası sil
    E-TelNo tablosu composite primary key kullandığı için TelCode ve TelNo birlikte gerekli
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'employee':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only employees can delete phone numbers"
            )
        
        # TelCode yoksa tüm TelCode'ları kontrol et veya sadece TelNo ile sil
        if telcode:
            delete_query = text(PROFILE["delete_employee_telno_with_code"])
            db.execute(delete_query, {"user_id": user_id, "telcode": telcode, "telno": telno})
        else:
            # TelCode belirtilmemişse, TelNo'ya göre sil (tüm TelCode'lar için)
            delete_query = text(PROFILE["delete_employee_telno"])
            db.execute(delete_query, {"user_id": user_id, "telno": telno})
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=telno_deleted",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting phone number: {str(e)}"
        )


@router.post("/add-email", tags=["Profile"])
async def add_email(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    email: str = Form(...),
):
    """
    Yeni email adresi ekle
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'employee':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only employees can add email addresses"
            )
        
        # Email adresi ekle - önce kolon adını bul
        columns_query = text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'E-MailAdress' AND COLUMN_NAME != 'EUserID'
            ORDER BY ORDINAL_POSITION
        """)
        columns_result = db.execute(columns_query)
        email_columns = [row[0] for row in columns_result.fetchall()]
        
        # Email kolonunu bul
        email_column = None
        for col in email_columns:
            if 'email' in col.lower() or 'mail' in col.lower():
                email_column = col
                break
        
        if not email_column and email_columns:
            email_column = email_columns[0]  # İlk kolonu kullan
        
        if email_column:
            insert_query = text(f"""
                INSERT INTO [E-MailAdress] (EUserID, [{email_column}])
                VALUES (:user_id, :email)
            """)
            db.execute(insert_query, {"user_id": user_id, "email": email})
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email kolonu bulunamadı"
            )
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=email_added",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding email address: {str(e)}"
        )


@router.post("/delete-email", tags=["Profile"])
async def delete_email(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    email: str = Form(...),
):
    """
    Email adresi sil
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'employee':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only employees can delete email addresses"
            )
        
        # Email adresi sil - önce kolon adını bul
        columns_query = text(PROFILE["get_email_columns"])
        columns_result = db.execute(columns_query)
        email_columns = [row[0] for row in columns_result.fetchall()]
        
        # Email kolonunu bul
        email_column = None
        for col in email_columns:
            if 'email' in col.lower() or 'mail' in col.lower():
                email_column = col
                break
        
        if not email_column and email_columns:
            email_column = email_columns[0]  # İlk kolonu kullan
        
        if email_column:
            delete_query = text(PROFILE["delete_employee_email"].replace("{email_column}", email_column))
            db.execute(delete_query, {"user_id": user_id, "email": email})
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email kolonu bulunamadı"
            )
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=email_deleted",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting email address: {str(e)}"
        )


@router.post("/add-customer-telno", tags=["Profile"])
async def add_customer_telno(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    telno: str = Form(...),
    telcode: Optional[str] = Form(None),
    mail_address: str = Form(...),
    department_name: str = Form(...),
    first_name: str = Form(...),
    middle_name: Optional[str] = Form(None),
    last_name: str = Form(...),
):
    """
    Customer için yeni telefon numarası ekle (CommunityCompany tablosuna)
    CommunityCompany tablosu composite PK (MailAddress, CUserID) kullanıyor
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'customer':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only customers can add phone numbers"
            )
        
        customer_id = get_customer_id(db, user_id)
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # TelCode yoksa varsayılan olarak +90 kullan
        if not telcode:
            telcode = '+90'
        
        # CommunityCompany'ye ekle (MailAddress ve CUserID composite PK)
        insert_query = text(PROFILE["add_customer_contact"])
        db.execute(insert_query, {
            "mail_address": mail_address,
            "customer_id": customer_id,
            "department_name": department_name,
            "telcode": telcode,
            "telno": telno,
            "first_name": first_name,
            "middle_name": middle_name if middle_name else None,
            "last_name": last_name
        })
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=telno_added",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding phone number: {str(e)}"
        )


@router.post("/delete-customer-telno", tags=["Profile"])
async def delete_customer_telno(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    mail_address: str = Form(...),
):
    """
    Customer için telefon numarası sil (CommunityCompany tablosundan)
    CommunityCompany tablosu composite PK (MailAddress, CUserID) kullanıyor
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'customer':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only customers can delete phone numbers"
            )
        
        customer_id = get_customer_id(db, user_id)
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # CommunityCompany'den sil (MailAddress ve CUserID ile)
        delete_query = text("""
            DELETE FROM CommunityCompany
            WHERE MailAddress = :mail_address AND CUserID = :customer_id
        """)
        db.execute(delete_query, {"mail_address": mail_address, "customer_id": customer_id})
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=telno_deleted",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting phone number: {str(e)}"
        )


@router.post("/update-customer-contact", tags=["Profile"])
async def update_customer_contact(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    old_mail_address: str = Form(...),
    mail_address: str = Form(...),
    department_name: str = Form(...),
    telcode: str = Form(...),
    telno: str = Form(...),
    first_name: str = Form(...),
    middle_name: Optional[str] = Form(None),
    last_name: str = Form(...),
):
    """
    Customer için iletişim kişisi güncelle (CommunityCompany tablosunda)
    CommunityCompany tablosu composite PK (MailAddress, CUserID) kullanıyor
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'customer':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only customers can update contacts"
            )
        
        customer_id = get_customer_id(db, user_id)
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Eğer MailAddress değiştiyse, önce eski kaydı sil, sonra yeni kaydı ekle
        if old_mail_address != mail_address:
            # Önce eski kaydı sil
            delete_query = text(PROFILE["update_customer_contact_delete"])
            db.execute(delete_query, {"old_mail_address": old_mail_address, "customer_id": customer_id})
            
            # Yeni kaydı ekle
            insert_query = text(PROFILE["update_customer_contact_insert"])
            db.execute(insert_query, {
                "mail_address": mail_address,
                "customer_id": customer_id,
                "department_name": department_name,
                "telcode": telcode,
                "telno": telno,
                "first_name": first_name,
                "middle_name": middle_name if middle_name else None,
                "last_name": last_name
            })
        else:
            # MailAddress aynıysa, sadece diğer alanları güncelle
            update_query = text(PROFILE["update_customer_contact"])
            db.execute(update_query, {
                "mail_address": mail_address,
                "customer_id": customer_id,
                "department_name": department_name,
                "telcode": telcode,
                "telno": telno,
                "first_name": first_name,
                "middle_name": middle_name if middle_name else None,
                "last_name": last_name
            })
        
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=contact_updated",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating contact: {str(e)}"
        )


@router.post("/delete-customer-contact", tags=["Profile"])
async def delete_customer_contact(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    mail_address: str = Form(...),
):
    """
    Customer için iletişim kişisi sil (CommunityCompany tablosundan)
    CommunityCompany tablosu composite PK (MailAddress, CUserID) kullanıyor
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        if user_type != 'customer':
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only customers can delete contacts"
            )
        
        customer_id = get_customer_id(db, user_id)
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # CommunityCompany'den sil (MailAddress ve CUserID ile)
        delete_query = text("""
            DELETE FROM CommunityCompany
            WHERE MailAddress = :mail_address AND CUserID = :customer_id
        """)
        db.execute(delete_query, {"mail_address": mail_address, "customer_id": customer_id})
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=contact_deleted",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting contact: {str(e)}"
        )


@router.post("/change-password", tags=["Profile"])
async def change_password(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """
    Şifre değiştir
    """
    try:
        user_id, user_type = get_user_info_from_cookie(auth_token)
        
        # Mevcut şifreyi kontrol et
        user_query = text(PROFILE["check_password"])
        user_data = db.execute(user_query, {"user_id": user_id}).mappings().first()
        
        if not user_data or user_data['Password'] != current_password:
            return RedirectResponse(
                url="/profile?error=wrong_password",
                status_code=http_status.HTTP_303_SEE_OTHER
            )
        
        # Yeni şifre kontrolü
        if new_password != confirm_password:
            return RedirectResponse(
                url="/profile?error=password_mismatch",
                status_code=http_status.HTTP_303_SEE_OTHER
            )
        
        # Şifreyi güncelle
        update_query = text(PROFILE["update_password"])
        db.execute(update_query, {"user_id": user_id, "new_password": new_password})
        db.commit()
        
        return RedirectResponse(
            url="/profile?success=password_changed",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )


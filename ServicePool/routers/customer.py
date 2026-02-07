from fastapi import APIRouter, Depends, HTTPException, Query, Request, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import text
from typing import Annotated, Optional, Dict, Any, List
from database import SessionLocal
from starlette import status as http_status
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates
from routers.auth import get_user_from_cookie, AUTH_TOKEN_COOKIE
import os
from dotenv import load_dotenv
from datetime import date
from queries import CUSTOMER

load_dotenv()

router = APIRouter(
    prefix="/customer",
    tags=["Customer"],
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
    query = text(CUSTOMER["get_customer_id"])
    result = db.execute(query, {"user_id": user_id}).scalar()
    return result

def get_auth_token_from_request(request: Request, auth_token: Optional[str] = None):
    """Cookie'yi hem parametre hem de request'ten al"""
    if not auth_token:
        auth_token = request.cookies.get(AUTH_TOKEN_COOKIE)
    return auth_token

def validate_customer_user(user_info: Optional[Dict], request: Request = None):
    """Customer kullanıcısını doğrula"""
    if not user_info:
        return False
    user_type = user_info.get('user_type', '').lower()
    # 'customer' veya 'CustomerCompany' kabul et
    return user_type in ['customer', 'customercompany']

@router.get("/offers", response_class=HTMLResponse)
async def get_customer_offers(
    request: Request,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Customer'ın offer'larını görüntüle"""
    # Cookie'yi request'ten de kontrol et
    auth_token = get_auth_token_from_request(request, auth_token)
    user_info = get_user_from_cookie(auth_token)
    
    # Customer kullanıcısını doğrula
    if not validate_customer_user(user_info):
        return RedirectResponse(url="/auth/login?error=no_token&role=customer", status_code=302)
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Customer'ın CompanyTradeName'ini al
        customer_name_query = text(CUSTOMER["get_customer_name"])
        customer_name = db.execute(customer_name_query, {"customer_id": customer_id}).scalar()
        
        if not customer_name:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Offer'ları view'den getir (tarih filtresi ile)
        where_clause = "WHERE v.Customer = :customer_name"
        params = {"customer_name": customer_name}
        date_filter = ""
        
        if start_date:
            where_clause += " AND v.OfferDate >= :start_date"
            date_filter += " AND v.OfferDate >= :start_date"
            params["start_date"] = start_date
        if end_date:
            where_clause += " AND v.OfferDate <= :end_date"
            date_filter += " AND v.OfferDate <= :end_date"
            params["end_date"] = end_date
        
        query = text(CUSTOMER["get_customer_offers"].format(date_filter=date_filter))
        
        offers = db.execute(query, params).mappings().all()
        
        return templates.TemplateResponse("customer_offers.html", {
            "request": request,
            "offers": offers,
            "start_date": start_date or "",
            "end_date": end_date or ""
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/offers/{offer_id}/accept")
async def accept_offer(
    offer_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Offer'ı kabul et ve Order'a dönüştür"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Offer'ı kontrol et
        offer_query = text(CUSTOMER["get_offer_for_accept"])
        offer = db.execute(offer_query, {"offer_id": offer_id, "customer_id": customer_id}).mappings().first()
        
        if not offer:
            raise HTTPException(status_code=404, detail="Offer bulunamadı veya size ait değil")
        
        if offer['Status'] != 'NotAccepted':
            raise HTTPException(status_code=400, detail="Sadece NotAccepted offer'lar kabul edilebilir")
        
        # Exchange rate'i Offer'dan al
        exchange_rate = float(offer['ExchangeRate']) if offer.get('ExchangeRate') else 30.0
        
        # sp_AcceptOffer procedure'ını kullan
        # Procedure şunları yapacak:
        # 1. Offer Status'u 'Accepted' yapacak
        # 2. Order oluşturacak
        # 3. OrderLine'ları kopyalayacak (eğer tablo varsa)
        # 4. SaleID döndürecek
        accept_offer_query = text(CUSTOMER["accept_offer"])
        result = db.execute(accept_offer_query, {
            "offer_no": offer_id,
            "payment_type": "CreditCard",  # Varsayılan değer
            "exchange_rate": exchange_rate
        })
        
        # Procedure'dan dönen SaleID'yi al
        order_id = result.scalar()
        
        db.commit()
        
        return {"status": "success", "message": "Offer kabul edildi ve Order oluşturuldu", "order_id": order_id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/offers/{offer_id}/details")
async def get_offer_details(
    offer_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Offer detaylarını getir (OfferLine'lar ile birlikte)"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        # Customer'ın CompanyTradeName'ini al
        customer_name_query = text(CUSTOMER["get_customer_name"])
        customer_name = db.execute(customer_name_query, {"customer_id": customer_id}).scalar()
        
        if not customer_name:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Offer bilgileri view'den
        offer_query = text(CUSTOMER["get_offer_details"])
        offer = db.execute(offer_query, {"offer_id": offer_id, "customer_name": customer_name}).mappings().first()
        
        if not offer:
            raise HTTPException(status_code=404, detail="Offer bulunamadı")
        
        # OfferLine'lar ve Product bilgileri view'den
        offer_lines_query = text(CUSTOMER["get_offer_line_details"])
        offer_lines = db.execute(offer_lines_query, {"offer_id": offer_id}).mappings().all()
        
        return {
            "offer": dict(offer),
            "offer_lines": [dict(line) for line in offer_lines]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/orders", response_class=HTMLResponse)

async def get_customer_orders(
    request: Request,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """Customer'ın order'larını görüntüle"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        return RedirectResponse(url="/auth/login?error=no_token&role=customer", status_code=302)
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Customer'ın CompanyTradeName'ini al
        customer_name_query = text(CUSTOMER["get_customer_name"])
        customer_name = db.execute(customer_name_query, {"customer_id": customer_id}).scalar()
        
        if not customer_name:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Order'ları view'den getir (tarih filtresi ile)
        where_clause = "WHERE v.Customer = :customer_name"
        params = {"customer_name": customer_name}
        date_filter = ""
        if start_date:
            where_clause += " AND v.SaleDate >= :start_date"
            date_filter += " AND v.SaleDate >= :start_date"
            params["start_date"] = start_date
        if end_date:
            where_clause += " AND v.SaleDate <= :end_date"
            date_filter += " AND v.SaleDate <= :end_date"
            params["end_date"] = end_date

        # Order tablosunda Status kolonu var, view'dan al
        query = text(CUSTOMER["get_customer_orders"].format(date_filter=date_filter))
        try:
            orders = db.execute(query, params).mappings().all()
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Orders sorgusu hatası: {str(e)}")
        
        return templates.TemplateResponse("customer_orders.html", {
            "request": request,
            "orders": orders,
            "start_date": start_date or "",
            "end_date": end_date or ""
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/orders/{order_id}/details")
async def get_order_details(
    order_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Order detaylarını getir (OrderLine'lar ve Product'lar ile birlikte)"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        # Customer'ın CompanyTradeName'ini al
        customer_name_query = text(CUSTOMER["get_customer_name"])
        customer_name = db.execute(customer_name_query, {"customer_id": customer_id}).scalar()
        
        if not customer_name:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Order bilgileri view'den (Offer, Order, Customer bilgileri bir arada)
        # Order tablosunda Status kolonu var, view'dan al
        order_query = text(CUSTOMER["get_order_details"])
        order = db.execute(order_query, {"order_id": order_id, "customer_name": customer_name}).mappings().first()

        
        if not order:
            raise HTTPException(status_code=404, detail="Order bulunamadı")
        
        # OrderLine'lar ve Product bilgileri view'den (OfferLine, Product bilgileri bir arada)
        # Order'ın OfferNo'sunu al
        order_offer_query = text(CUSTOMER["get_order_offer_no"])
        order_offer = db.execute(order_offer_query, {"order_id": order_id, "customer_name": customer_name}).scalar()
        
        if not order_offer:
            raise HTTPException(status_code=404, detail="Order bulunamadı")
        
        # OrderLine'lar ve SerialNumber'ları al
        # Trigger (trg_Order_PostInsert_Process) Order oluşturulduğunda Product tablosundaki SerialNumber'ları CUserID ile güncelliyor
        # Bu yüzden Product tablosundan bu customer'a ait ve bu ProductCode'a uygun SerialNumber'ları alıyoruz
        order_lines_query = text(CUSTOMER["get_order_line_details"])
        order_lines = db.execute(order_lines_query, {"offer_no": order_offer, "customer_id": customer_id}).mappings().all()

        return {
            "order": dict(order),
            "order_lines": [dict(line) for line in order_lines]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/products", response_class=HTMLResponse)
async def get_customer_products_page(
    request: Request,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Customer'ın sahip olduğu product'ları göster"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        return RedirectResponse(url="/auth/login?error=no_token&role=customer", status_code=302)
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Customer'ın sahip olduğu product'ları getir
        try:
            products_query = text(CUSTOMER["get_customer_products"])
            products = db.execute(products_query, {"customer_id": customer_id}).mappings().all()
            products_list = [dict(p) for p in products]
            
            return templates.TemplateResponse("customer_products.html", {
                "request": request,
                "products": products_list,
                "token": auth_token
            })
        except Exception as query_error:
            import traceback
            traceback.print_exc()
            # Hata durumunda boş liste ile devam et
            return templates.TemplateResponse("customer_products.html", {
                "request": request,
                "products": [],
                "token": auth_token,
                "error": str(query_error)
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/products/api")
async def get_customer_products(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Customer'ın sahip olduğu product'ları getir (API)"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Customer'ın sahip olduğu product'ları getir (IsRepair = 0 olanlar)
        products_query = text(CUSTOMER["get_customer_products_api"])
        products = db.execute(products_query, {"customer_id": customer_id}).mappings().all()
        
        return {"products": [dict(p) for p in products]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair-requests/create")
async def create_repair_request(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    serial_number: str = Form(...)
):
    """Product için repair request oluştur (sadece SerialNumber ile)"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        if not serial_number or not serial_number.strip():
            raise HTTPException(status_code=400, detail="SerialNumber zorunludur")
        
        # Product'ın customer'a ait olduğunu ve IsRepair = 0 olduğunu kontrol et
        product_check = text(CUSTOMER["check_product_for_repair"])
        product = db.execute(product_check, {"serial_number": serial_number, "customer_id": customer_id}).mappings().first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product bulunamadı veya size ait değil")
        
        # IsRepair kontrolü (BIT tipinde 0 veya 1 olabilir)
        is_repair = product['IsRepair']
        if is_repair == 1 or is_repair == True:
            raise HTTPException(status_code=400, detail="Bu ürün zaten tamir sürecinde")
        
        # RepairRequest oluştur (Status default 'NOT COMPLETED' - schema'ya göre)
        # Status değerleri: 'NotAccepted', 'Accepted', 'Rejected' (CHECK constraint'e göre)
        request_date = datetime.now()
        create_request_query = text(CUSTOMER["create_repair_request"])
        try:
            result = db.execute(create_request_query, {
                "serial_number": serial_number,
                "request_date": request_date
            })
            repair_request_id = result.scalar()
            db.commit()
            
            return {"status": "success", "message": "Repair request oluşturuldu", "repair_request_id": repair_request_id}
        except Exception as insert_error:
            db.rollback()
            # Eğer Status hatası varsa, default değeri kullanmayı dene
            error_str = str(insert_error)
            if "Status" in error_str or "CHECK" in error_str or "constraint" in error_str.lower():
                create_request_query_default = text(CUSTOMER["create_repair_request_default"])
                result = db.execute(create_request_query_default, {
                    "serial_number": serial_number,
                    "request_date": request_date
                })
                repair_request_id = result.scalar()
                db.commit()
                return {"status": "success", "message": "Repair request oluşturuldu", "repair_request_id": repair_request_id}
            raise HTTPException(status_code=500, detail=f"Repair request oluşturulurken hata: {error_str}")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/repair-requests", response_class=HTMLResponse)
async def get_customer_repair_requests(
    request: Request,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Customer'ın repair request'lerini görüntüle"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        return RedirectResponse(url="/auth/login?error=no_token&role=customer", status_code=302)
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # RepairRequest'leri getir (tarih filtresi ile)
        # SerialNumber üzerinden Product'a bağlanarak customer kontrolü yap
        where_clause = """WHERE EXISTS (
            SELECT 1 FROM Product p
            WHERE p.SerialNumber = rr.SerialNumber AND p.CUserID = :customer_id
        )"""
        params = {"customer_id": customer_id}
        date_filter = ""
        
        if start_date:
            where_clause += " AND rr.Date >= :start_date"
            date_filter += " AND rr.Date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            where_clause += " AND rr.Date <= :end_date"
            date_filter += " AND rr.Date <= :end_date"
            params["end_date"] = end_date
        
        # RepairRequest'leri Product bilgileri ile birlikte getir
        query = text(CUSTOMER["get_customer_repair_requests"].format(date_filter=date_filter))
        
        repair_requests = db.execute(query, params).mappings().all()
        
        return templates.TemplateResponse("customer_repair_requests.html", {
            "request": request,
            "repair_requests": repair_requests,
            "start_date": start_date or "",
            "end_date": end_date or ""
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair-requests/{repair_request_id}/cancel")
async def cancel_repair_request(
    repair_request_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Repair request'i iptal et (customer)"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        # RepairRequest'i kontrol et (SerialNumber üzerinden Product'a bağlayarak)
        check_query = text(CUSTOMER["check_repair_request"])
        repair_request = db.execute(check_query, {"repair_request_id": repair_request_id, "customer_id": customer_id}).mappings().first()
        
        if not repair_request:
            raise HTTPException(status_code=404, detail="Repair request bulunamadı veya size ait değil")
        
        if repair_request['Status'] in ['Completed', 'Cancelled', 'Rejected']:
            raise HTTPException(status_code=400, detail="Bu repair request iptal edilemez")
        
        # Status'u Cancelled yap
        update_query = text(CUSTOMER["cancel_repair_request"])
        db.execute(update_query, {"repair_request_id": repair_request_id})
        db.commit()
        
        return {"status": "success", "message": "Repair request iptal edildi"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/feedback", response_class=HTMLResponse)
async def get_customer_feedback(
    request: Request,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Customer'ın feedback'lerini görüntüle"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        return RedirectResponse(url="/auth/login?error=no_token&role=customer", status_code=302)
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Customer'ın CompanyTradeName'ini al
        customer_name_query = text(CUSTOMER["get_customer_name"])
        customer_name = db.execute(customer_name_query, {"customer_id": customer_id}).scalar()
        
        if not customer_name:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Feedback'leri view'den getir (tarih filtresi ile)
        where_clause = "WHERE vf.CompanyTradeName = :customer_name"
        params = {"customer_name": customer_name}
        date_filter = ""
        
        if start_date:
            where_clause += " AND vf.Date >= :start_date"
            date_filter += " AND vf.Date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            where_clause += " AND vf.Date <= :end_date"
            date_filter += " AND vf.Date <= :end_date"
            params["end_date"] = end_date
        
        query = text(CUSTOMER["get_customer_feedback"].format(date_filter=date_filter))
        params["customer_id"] = customer_id
        
        try:
            feedbacks = db.execute(query, params).mappings().all()
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Feedback sorgusu hatası: {str(e)}")
        
        return templates.TemplateResponse("customer_feedback.html", {
            "request": request,
            "feedbacks": feedbacks,
            "start_date": start_date or "",
            "end_date": end_date or ""
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/orders/{order_id}/feedback")
async def create_order_feedback(
    order_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    rating: Optional[int] = Query(None),
    comment: Optional[str] = Query(None)
):
    """Order için feedback oluştur (customer)"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        if not rating or rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating 1-5 arasında olmalıdır")
        
        # Order'ın customer'a ait olduğunu kontrol et (Offer üzerinden)
        order_check = text(CUSTOMER["check_order_for_feedback"])
        order_exists = db.execute(order_check, {"order_id": order_id, "customer_id": customer_id}).scalar()
        
        if not order_exists:
            raise HTTPException(status_code=404, detail="Order bulunamadı veya size ait değil")
        
        # Feedback oluştur (CustomerFeedback tablosu kullan)
        feedback_date = datetime.now()
        create_feedback_query = text(CUSTOMER["create_feedback"])
        result = db.execute(create_feedback_query, {
            "sale_id": order_id,
            "customer_id": customer_id,
            "rating": rating,
            "feedback_text": comment,
            "feedback_date": feedback_date
        })
        feedback_id = result.scalar()
        
        db.commit()
        
        return {"status": "success", "message": "Feedback oluşturuldu", "feedback_id": feedback_id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.put("/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None),
    rating: Optional[int] = Query(None),
    comment: Optional[str] = Query(None)
):
    """Feedback güncelle"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        if not rating or rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating 1-5 arasında olmalıdır")
        
        # Feedback'in customer'a ait olduğunu kontrol et
        check_query = text(CUSTOMER["check_feedback"])
        feedback_exists = db.execute(check_query, {"feedback_id": feedback_id, "customer_id": customer_id}).scalar()
        
        if not feedback_exists:
            raise HTTPException(status_code=404, detail="Feedback bulunamadı veya size ait değil")
        
        # Feedback'i güncelle
        update_query = text(CUSTOMER["update_feedback"])
        db.execute(update_query, {
            "feedback_id": feedback_id,
            "rating": rating,
            "feedback_text": comment
        })
        
        db.commit()
        
        return {"status": "success", "message": "Feedback güncellendi"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Feedback sil"""
    user_info = get_user_from_cookie(auth_token)
    if not user_info or user_info.get('user_type') != 'customer':
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_id = user_info.get('id')
        customer_id = get_customer_id(db, user_id)
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="Customer bulunamadı")
        
        # Feedback'in customer'a ait olduğunu kontrol et
        check_query = text(CUSTOMER["check_feedback"])
        feedback_exists = db.execute(check_query, {"feedback_id": feedback_id, "customer_id": customer_id}).scalar()
        
        if not feedback_exists:
            raise HTTPException(status_code=404, detail="Feedback bulunamadı veya size ait değil")
        
        # Feedback'i sil
        delete_query = text(CUSTOMER["delete_feedback"])
        db.execute(delete_query, {"feedback_id": feedback_id})
        
        db.commit()
        
        return {"status": "success", "message": "Feedback silindi"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


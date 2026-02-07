from fastapi import APIRouter, Depends, HTTPException, Query, Cookie, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated, Optional
from database import SessionLocal
from routers.auth import get_user_from_cookie
from queries import EMPLOYEE

router = APIRouter(
    prefix="/employee",
    tags=["Employee"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.get("/repair-requests")
async def get_repair_requests(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Tüm repair request'leri getir (employee)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # RepairRequest'leri Product bilgileri ile birlikte getir
        query = text(EMPLOYEE["get_repair_requests"])
        repair_requests = db.execute(query).mappings().all()
        
        return JSONResponse({
            "repair_requests": [dict(rr) for rr in repair_requests]
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair-requests/{repair_request_id}/accept")
async def accept_repair_request(
    repair_request_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Repair request'i kabul et (Status'u Accepted yap)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # RepairRequest'i kontrol et
        check_query = text(EMPLOYEE["check_repair_request"])
        repair_request = db.execute(check_query, {"repair_request_id": repair_request_id}).mappings().first()
        
        if not repair_request:
            raise HTTPException(status_code=404, detail="Repair request bulunamadı")
        
        if repair_request['Status'] in ['Completed', 'Cancelled', 'Rejected']:
            raise HTTPException(status_code=400, detail="Bu repair request zaten işlenmiş")
        
        # Status'u Accepted yap
        update_query = text(EMPLOYEE["accept_repair_request"])
        db.execute(update_query, {"repair_request_id": repair_request_id})
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Repair request kabul edildi"
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair-requests/{repair_request_id}/reject")
async def reject_repair_request(
    repair_request_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Repair request'i reddet (Status'u Rejected yap)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # RepairRequest'i kontrol et
        check_query = text(EMPLOYEE["check_repair_request"])
        repair_request = db.execute(check_query, {"repair_request_id": repair_request_id}).mappings().first()
        
        if not repair_request:
            raise HTTPException(status_code=404, detail="Repair request bulunamadı")
        
        if repair_request['Status'] in ['Completed', 'Cancelled', 'Rejected']:
            raise HTTPException(status_code=400, detail="Bu repair request zaten işlenmiş")
        
        # Status'u Rejected yap
        update_query = text(EMPLOYEE["reject_repair_request"])
        db.execute(update_query, {"repair_request_id": repair_request_id})
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Repair request reddedildi"
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair-requests/{repair_request_id}/assign-technician")
async def assign_technician(
    repair_request_id: int,
    db: db_dependency,
    technician_id: int = Query(...),
    auth_token: Optional[str] = Cookie(None)
):
    """Repair request'e teknisyen ata"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # RepairRequest'i kontrol et
        check_query = text(EMPLOYEE["check_repair_request"])
        repair_request = db.execute(check_query, {"repair_request_id": repair_request_id}).mappings().first()
        
        if not repair_request:
            raise HTTPException(status_code=404, detail="Repair request bulunamadı")
        
        if repair_request['Status'] != 'Pending':
            raise HTTPException(status_code=400, detail="Sadece Pending durumundaki repair request'lere teknisyen atanabilir")
        
        # Teknisyenin Technician tablosunda olduğunu kontrol et
        technician_check = text(EMPLOYEE["check_technician"])
        technician_exists = db.execute(technician_check, {"technician_id": technician_id}).scalar()
        
        if not technician_exists:
            raise HTTPException(status_code=404, detail="Teknisyen bulunamadı")
        
        # RepairRequest'e teknisyen ata (TUserID kolonu varsa)
        # Eğer RepairRequest tablosunda TUserID kolonu yoksa, başka bir tablo kullanılıyor olabilir
        # Önce kolonları kontrol et
        columns_check = text(EMPLOYEE["check_repair_request_columns"])
        columns = db.execute(columns_check).fetchall()
        column_names = [col[0] for col in columns]
        
        if 'TUserID' in column_names:
            update_query = text(EMPLOYEE["assign_technician_with_tuserid"])
        else:
            # TUserID kolonu yoksa sadece status'u güncelle
            update_query = text(EMPLOYEE["assign_technician_without_tuserid"])
        
        db.execute(update_query, {
            "technician_id": technician_id,
            "repair_request_id": repair_request_id
        })
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Teknisyen başarıyla atandı"
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.get("/repair-requests/technicians")
async def get_technicians(
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Teknisyen listesini getir"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # Teknisyenleri getir (EUserID kullanarak)
        technicians_query = text(EMPLOYEE["get_technicians"])
        technicians = db.execute(technicians_query).mappings().all()
        
        return JSONResponse({
            "technicians": [dict(tech) for tech in technicians]
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair/create")
async def create_repair(
    repair_request_id: int = Form(...),
    technician_id: int = Form(...),
    db: db_dependency = Depends(get_db),
    auth_token: Optional[str] = Cookie(None)
):
    """Repair oluştur (Accepted repair request için)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # RepairRequest'i kontrol et (Status = 'Accepted' olmalı)
        check_query = text(EMPLOYEE["check_repair_request"])
        repair_request = db.execute(check_query, {"repair_request_id": repair_request_id}).mappings().first()
        
        if not repair_request:
            raise HTTPException(status_code=404, detail="Repair request bulunamadı")
        
        if repair_request['Status'] != 'Accepted':
            raise HTTPException(status_code=400, detail="Sadece Accepted durumundaki repair request'ler için repair oluşturulabilir")
        
        # Technician'ı kontrol et
        technician_check = text(EMPLOYEE["check_technician_by_euserid"])
        technician_exists = db.execute(technician_check, {"technician_id": technician_id}).scalar()
        
        if not technician_exists:
            raise HTTPException(status_code=404, detail="Teknisyen bulunamadı")
        
        # Repair oluştur
        create_repair_query = text(EMPLOYEE["create_repair"])
        result = db.execute(create_repair_query, {
            "repair_request_id": repair_request_id,
            "technician_id": technician_id
        })
        repair_id = result.scalar()
        
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Repair oluşturuldu",
            "repair_id": repair_id
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/repair/{repair_id}/complete")
async def complete_repair(
    repair_id: int,
    db: db_dependency,
    auth_token: Optional[str] = Cookie(None)
):
    """Repair'i tamamla (Response = 'COMPLETED' yap - trigger otomatik olarak RepairRequest.Status'u 'COMPLETED' yapacak)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # Repair'i kontrol et
        check_query = text(EMPLOYEE["check_repair"])
        repair = db.execute(check_query, {"repair_id": repair_id}).mappings().first()
        
        if not repair:
            raise HTTPException(status_code=404, detail="Repair bulunamadı")
        
        if repair['Response'] == 'COMPLETED':
            raise HTTPException(status_code=400, detail="Bu repair zaten tamamlanmış")
        
        # Response'u COMPLETED yap (trigger otomatik olarak RepairRequest.Status'u ve EndDate'i güncelleyecek)
        update_query = text(EMPLOYEE["complete_repair"])
        db.execute(update_query, {"repair_id": repair_id})
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Repair tamamlandı"
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/orders/{order_id}/update-status")
async def update_order_status(
    order_id: int,
    db: db_dependency,
    status: str = Query(..., description="Order status: Active, Completed, Cancelled, NotAccepted"),
    auth_token: Optional[str] = Cookie(None)
):
    """Order status'unu güncelle (employee)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # Geçerli status değerlerini kontrol et
        valid_statuses = ['NotCompleted', 'Completed', 'Cancelled', 'NotAccepted', 'Active']
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Geçersiz status. Geçerli değerler: {', '.join(valid_statuses)}")
        
        # Order'ın var olup olmadığını kontrol et
        check_query = text(EMPLOYEE["check_order"])
        order_exists = db.execute(check_query, {"order_id": order_id}).scalar()
        
        if not order_exists:
            raise HTTPException(status_code=404, detail="Order bulunamadı")
        
        # Order tablosunda Status kolonu var, direkt güncelle
        update_query = text(EMPLOYEE["update_order_status"])
        
        db.execute(update_query, {
            "status": status,
            "order_id": order_id
        })
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": f"Order status'u '{status}' olarak güncellendi",
            "order_id": order_id
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/inventory/create")
async def create_inventory(
    db: db_dependency,
    product_code: str = Form(...),
    product_description: str = Form(...),
    purchase_unit_price: float = Form(...),
    product_type: str = Form(...),
    cpu: Optional[int] = Form(None),
    ram: Optional[int] = Form(None),
    disk: Optional[str] = Form(None),
    disk_type: Optional[str] = Form(None),
    disk_space: Optional[str] = Form(None),
    disk_count: Optional[int] = Form(None),
    auth_token: Optional[str] = Cookie(None)
):
    """ProductInventory oluştur (Server, Storage veya Other)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # ProductInventory zaten var mı kontrol et
        check_query = text(EMPLOYEE["check_product_inventory_exists"])
        existing = db.execute(check_query, {"product_code": product_code}).scalar()
        if existing:
            raise HTTPException(status_code=400, detail=f"ProductCode '{product_code}' zaten mevcut")
        
        # ProductInventory oluştur (stok değerleri trigger'lar ile otomatik belirlenecek)
        create_inventory_query = text(EMPLOYEE["create_product_inventory"])
        db.execute(create_inventory_query, {
            "product_code": product_code,
            "product_description": product_description,
            "purchase_unit_price": purchase_unit_price,
            "product_type": product_type
        })
        
        # ProductType'a göre ilgili inventory tablosuna ekle
        if product_type == 'Server':
            if not cpu or not ram or not disk:
                raise HTTPException(status_code=400, detail="Server için CPU, RAM ve Disk zorunludur")
            create_server_inv_query = text(EMPLOYEE["create_server_inventory"])
            db.execute(create_server_inv_query, {
                "product_code": product_code,
                "cpu": cpu,
                "ram": ram,
                "disk": disk
            })
        elif product_type == 'Storage':
            if not disk_type or not disk_space or disk_count is None:
                raise HTTPException(status_code=400, detail="Storage için DiskType, DiskSpace ve DiskCount zorunludur")
            create_storage_inv_query = text(EMPLOYEE["create_storage_inventory"])
            db.execute(create_storage_inv_query, {
                "product_code": product_code,
                "disk_type": disk_type,
                "disk_space": disk_space,
                "disk_count": disk_count
            })
        # Other type için ek bir tablo yok, sadece ProductInventory yeterli
        
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "ProductInventory başarıyla oluşturuldu",
            "product_code": product_code
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@router.post("/product/create")
async def create_product(
    db: db_dependency,
    serial_number: str = Form(...),
    product_code: str = Form(...),
    name: str = Form(...),
    mac_address: str = Form(...),
    firmware_version: str = Form(...),
    product_type: str = Form(...),
    ip_address: Optional[str] = Form(None),
    operating_system: Optional[str] = Form(None),
    service: Optional[str] = Form(None),
    mgmt_ip1: Optional[str] = Form(None),
    mgmt_ip2: Optional[str] = Form(None),
    service_ip1: Optional[str] = Form(None),
    service_ip2: Optional[str] = Form(None),
    lun: Optional[str] = Form(None),
    capacity: Optional[int] = Form(None),
    auth_token: Optional[str] = Cookie(None)
):
    """Product oluştur (Server, Storage veya Other)"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token gerekli")
    
    try:
        user_info = get_user_from_cookie(auth_token)
        if not user_info or user_info.get('user_type') != 'employee':
            raise HTTPException(status_code=403, detail="Bu işlem için employee yetkisi gerekli")
        
        # ProductInventory var mı kontrol et
        check_inv_query = text(EMPLOYEE["check_product_inventory_exists"])
        inventory_exists = db.execute(check_inv_query, {"product_code": product_code}).scalar()
        if not inventory_exists:
            raise HTTPException(status_code=404, detail=f"ProductCode '{product_code}' ProductInventory'de bulunamadı. Önce inventory oluşturun.")
        
        # ProductInventory'den ProductType'ı al
        get_type_query = text("SELECT ProductType FROM ProductInventory WHERE ProductCode = :product_code")
        inv_type = db.execute(get_type_query, {"product_code": product_code}).scalar()
        if inv_type != product_type:
            raise HTTPException(status_code=400, detail=f"ProductType uyuşmuyor. Inventory'de '{inv_type}', gönderilen '{product_type}'")
        
        # SerialNumber zaten var mı kontrol et
        check_product_query = text(EMPLOYEE["check_product_exists"])
        existing_product = db.execute(check_product_query, {"serial_number": serial_number}).scalar()
        if existing_product:
            raise HTTPException(status_code=400, detail=f"SerialNumber '{serial_number}' zaten mevcut")
        
        # MacAddress zaten var mı kontrol et
        check_mac_query = text(EMPLOYEE["check_mac_address_exists"])
        existing_mac = db.execute(check_mac_query, {"mac_address": mac_address}).scalar()
        if existing_mac:
            raise HTTPException(status_code=400, detail=f"MacAddress '{mac_address}' zaten mevcut")
        
        # Product oluştur
        create_product_query = text(EMPLOYEE["create_product"])
        db.execute(create_product_query, {
            "serial_number": serial_number,
            "name": name,
            "mac_address": mac_address,
            "firmware_version": firmware_version,
            "is_repair": 0,
            "c_user_id": None  # İlk oluşturulduğunda customer'a atanmamış
        })
        
        # ProductType'a göre ilgili tabloya ekle
        if product_type == 'Server':
            if not ip_address or not service:
                raise HTTPException(status_code=400, detail="Server için IPAddress ve Service zorunludur")
            # ServerInventory var mı kontrol et
            check_server_inv_query = text(EMPLOYEE["check_server_inventory_exists"])
            server_inv_exists = db.execute(check_server_inv_query, {"product_code": product_code}).scalar()
            if not server_inv_exists:
                raise HTTPException(status_code=404, detail=f"ProductCode '{product_code}' ServerInventory'de bulunamadı")
            create_server_query = text(EMPLOYEE["create_server"])
            db.execute(create_server_query, {
                "serial_number": serial_number,
                "ip_address": ip_address,
                "operating_system": operating_system,
                "service": service,
                "product_code": product_code
            })
        elif product_type == 'Storage':
            if not mgmt_ip1 or not mgmt_ip2 or not service_ip1 or not service_ip2 or not lun or not capacity:
                raise HTTPException(status_code=400, detail="Storage için tüm IP adresleri, LUN ve Capacity zorunludur")
            # StorageInventory var mı kontrol et
            check_storage_inv_query = text(EMPLOYEE["check_storage_inventory_exists"])
            storage_inv_exists = db.execute(check_storage_inv_query, {"product_code": product_code}).scalar()
            if not storage_inv_exists:
                raise HTTPException(status_code=404, detail=f"ProductCode '{product_code}' StorageInventory'de bulunamadı")
            create_storage_query = text(EMPLOYEE["create_storage"])
            db.execute(create_storage_query, {
                "serial_number": serial_number,
                "mgmt_ip1": mgmt_ip1,
                "mgmt_ip2": mgmt_ip2,
                "service_ip1": service_ip1,
                "service_ip2": service_ip2,
                "lun": lun,
                "capacity": capacity,
                "product_code": product_code
            })
        # Other type için ek bir tablo yok, sadece Product yeterli
        
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Product başarıyla oluşturuldu",
            "serial_number": serial_number
        })
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


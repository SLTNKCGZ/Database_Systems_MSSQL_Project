from fastapi import FastAPI, Depends, Request
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from database import SessionLocal
from routers import auth, tables, employee_management, profile, customer, employee
from typing import Annotated

load_dotenv()

app = FastAPI(
    title="ServicePool API",
    description="ServicePool Authentication and Management System"
)

# Include routers
app.include_router(auth.router)
app.include_router(tables.router)
app.include_router(employee_management.router)
app.include_router(profile.router)
app.include_router(customer.router)
app.include_router(employee.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse, tags=["General"])
async def index():
    """Redirect to login page"""
    return RedirectResponse(url="/auth/login?role=employee", status_code=302)

@app.get("/demo", tags=["General"])
def demo(db: db_dependency):
    """Demo endpoint to test database connection"""
    users = db.execute(text("SELECT * FROM [User]"))
    return users.mappings().all()


# Redirect old endpoints to new auth endpoints for backward compatibility
@app.get("/login", response_class=HTMLResponse, tags=["General"])
async def redirect_login():
    """Redirect to auth login page"""
    return RedirectResponse(url="/auth/login?role=employee", status_code=302)


@app.get("/register", response_class=HTMLResponse, tags=["General"])
async def redirect_register():
    """Redirect to auth register page"""
    return RedirectResponse(url="/auth/register?role=employee", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse, tags=["General"])
async def dashboard(request: Request):
    """Dashboard page after successful login"""
    from routers.auth import get_user_from_cookie, AUTH_TOKEN_COOKIE
    
    auth_token = request.cookies.get(AUTH_TOKEN_COOKIE)
    user_info = get_user_from_cookie(auth_token)
    
    if not user_info:
        return RedirectResponse(url="/auth/login?error=no_token", status_code=302)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_type": user_info.get('user_type', 'employee')
    })



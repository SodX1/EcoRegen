from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from datetime import datetime, timedelta

from .database import Base, engine, SessionLocal
from . import models
from app.features.auth.routes import router as auth_router
from app.features.auth.utils import SECRET_KEY, ALGORITHM
from .models import User
from .models import Task
from app.features.tasks.routes import router as tasks_router
from app.features.admin.routes import router as admin_router
from app.features.segmentation.routes import router as segmentation_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoRegen")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(admin_router)
app.include_router(segmentation_router)


# --- служебная функция для получения пользователя из cookie ---
def get_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()
    return user


@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    """Добавляем user в request.state, чтобы шаблоны знали, кто вошёл."""
    request.state.user = get_user_from_cookie(request)
    response = await call_next(request)
    return response


@app.get("/")
def home(request: Request, start_date: str | None = None, end_date: str | None = None):
    if not request.state.user:
        return RedirectResponse(url="/login", status_code=303)

    # Показываем задачи на главной странице с опциональной фильтрацией по дате.
    db = SessionLocal()
    try:
        query = db.query(Task)
        try:
            if start_date:
                sd = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Task.created_at >= sd)
            if end_date:
                ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(Task.created_at < ed)
        except Exception:
            start_date = None
            end_date = None

        tasks = query.order_by(Task.created_at.desc()).limit(20).all()
    finally:
        db.close()
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": request.state.user,
            "tasks": tasks,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@app.get("/segmentation")
def segmentation_page(request: Request):
    """Display segmentation tool page."""
    return templates.TemplateResponse(
        "segmentation.html",
        {"request": request},
    )
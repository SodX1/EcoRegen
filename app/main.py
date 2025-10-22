from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError

from .database import Base, engine, SessionLocal
from . import models
from .auth.routes import router as auth_router
from .auth.utils import SECRET_KEY, ALGORITHM
from .models import User

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
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "user": request.state.user})
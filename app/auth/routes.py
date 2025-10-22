# app/auth/routes.py
from fastapi import (
    APIRouter, Depends, HTTPException, status, Request, Form
)
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import ValidationError

from ..dependencies import get_db
from ..models import User
from .schemas import UserCreate, UserOut
from .utils import get_password_hash, verify_password, create_access_token
from .utils import SECRET_KEY, ALGORITHM

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Auth"])


# === Регистрация ===
@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str | None = None):
    token = request.cookies.get("access_token")
    if token:
        try:
            token = token.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub"):
                return RedirectResponse("/", status_code=303)
        except JWTError:
            pass
    return templates.TemplateResponse("register.html", {"request": request, "error": error})


@router.post("/register/form", response_class=HTMLResponse)
def register_form(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None),
    db: Session = Depends(get_db),
):
    if db.query(User).filter((User.email == email) | (User.username == username)).first():
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пользователь с таким email или именем уже существует."},
        )

    try:
        _ = UserCreate(email=email, username=username, password=password, full_name=full_name)
    except ValidationError as e:
        err = e.errors()[0]
        field = err["loc"][0]
        msg = err["msg"]
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"{field}: {msg}"},
        )

    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash(password),
    )
    db.add(user)
    db.commit()

    # создаём токен и сохраняем в cookie
    token = create_access_token(subject=user.email)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response


# === Авторизация ===
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None):
    token = request.cookies.get("access_token")
    if token:
        try:
            token = token.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub"):
                return RedirectResponse("/", status_code=303)
        except JWTError:
            pass
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login/form")
def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль."},
        )

    token = create_access_token(subject=user.email)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response


# === Выход ===
@router.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response

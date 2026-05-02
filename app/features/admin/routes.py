from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User, Task
from app.features.auth.utils import get_password_hash

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/admin", tags=["Admin"])


def check_admin(request: Request):
    """Проверяет, является ли пользователь администратором."""
    if not request.state.user or not request.state.user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return request.state.user


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Главная страница админ панели с статистикой."""
    admin = check_admin(request)
    
    users_count = db.query(User).count()
    tasks_count = db.query(Task).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": admin,
        "users_count": users_count,
        "tasks_count": tasks_count,
        "active_users": active_users,
    })


# ==================== Управление пользователями ====================

@router.get("/users", response_class=HTMLResponse)
def list_users(request: Request, db: Session = Depends(get_db)):
    """Список всех пользователей."""
    admin = check_admin(request)
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    return templates.TemplateResponse("admin/users_list.html", {
        "request": request,
        "user": admin,
        "users": users,
    })


@router.get("/users/add", response_class=HTMLResponse)
def add_user_page(request: Request, error: str | None = None):
    """Страница добавления пользователя."""
    admin = check_admin(request)
    return templates.TemplateResponse("admin/add_user.html", {
        "request": request,
        "user": admin,
        "error": error,
    })


@router.post("/users/add")
def add_user(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    full_name: str | None = Form(None),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Добавляет нового пользователя."""
    admin = check_admin(request)
    
    # Проверяем уникальность email и username
    if db.query(User).filter((User.email == email) | (User.username == username)).first():
        return templates.TemplateResponse("admin/add_user.html", {
            "request": request,
            "user": admin,
            "error": "Пользователь с таким email или именем уже существует.",
        })
    
    # Создаём пользователя
    new_user = User(
        email=email,
        username=username,
        full_name=full_name or "",
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
    )
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/admin/users?success=Пользователь добавлен", status_code=303)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def edit_user_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Страница редактирования пользователя."""
    admin = check_admin(request)
    user_to_edit = db.query(User).filter(User.id == user_id).first()
    
    if not user_to_edit:
        return RedirectResponse(url="/admin/users", status_code=303)
    
    return templates.TemplateResponse("admin/edit_user.html", {
        "request": request,
        "user": admin,
        "edit_user": user_to_edit,
    })


@router.post("/users/{user_id}/edit")
def edit_user(
    request: Request,
    user_id: int,
    email: str = Form(...),
    username: str = Form(...),
    full_name: str | None = Form(None),
    is_active: bool = Form(False),
    is_admin: bool = Form(False),
    password: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Редактирует пользователя."""
    admin = check_admin(request)
    user_to_edit = db.query(User).filter(User.id == user_id).first()
    
    if not user_to_edit:
        return RedirectResponse(url="/admin/users", status_code=303)
    
    # Проверяем уникальность email/username (кроме самого себя)
    if email != user_to_edit.email and db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("admin/edit_user.html", {
            "request": request,
            "user": admin,
            "edit_user": user_to_edit,
            "error": "Email уже используется другим пользователем",
        })
    
    if username != user_to_edit.username and db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse("admin/edit_user.html", {
            "request": request,
            "user": admin,
            "edit_user": user_to_edit,
            "error": "Username уже используется другим пользователем",
        })
    
    # Обновляем данные
    user_to_edit.email = email
    user_to_edit.username = username
    user_to_edit.full_name = full_name or ""
    user_to_edit.is_active = is_active
    user_to_edit.is_admin = is_admin
    
    # Обновляем пароль если указан новый
    if password:
        user_to_edit.hashed_password = get_password_hash(password)
    
    db.add(user_to_edit)
    db.commit()
    
    return RedirectResponse(url="/admin/users?success=Пользователь обновлен", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Удаляет пользователя."""
    admin = check_admin(request)
    
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        return RedirectResponse(url="/admin/users", status_code=303)
    
    # Не удаляем самого себя
    if user_to_delete.id == admin.id:
        return RedirectResponse(
            url="/admin/users?error=Нельзя удалить собственный аккаунт",
            status_code=303
        )
    
    db.delete(user_to_delete)
    db.commit()
    
    return RedirectResponse(url="/admin/users?success=Пользователь удален", status_code=303)


# ==================== Управление задачами ====================

@router.get("/tasks", response_class=HTMLResponse)
def list_tasks(request: Request, db: Session = Depends(get_db)):
    """Список всех задач для редактирования."""
    admin = check_admin(request)
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    
    return templates.TemplateResponse("admin/tasks_list.html", {
        "request": request,
        "user": admin,
        "tasks": tasks,
    })


@router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task_page(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Страница редактирования задачи."""
    admin = check_admin(request)
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        return RedirectResponse(url="/admin/tasks", status_code=303)
    
    users = db.query(User).all()
    
    return templates.TemplateResponse("admin/edit_task.html", {
        "request": request,
        "user": admin,
        "task": task,
        "users": users,
    })


@router.post("/tasks/{task_id}/edit")
def edit_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    owner_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """Редактирует задачу."""
    admin = check_admin(request)
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        return RedirectResponse(url="/admin/tasks", status_code=303)
    
    task.title = title
    task.description = description or ""
    
    # Если owner_id пуст, устанавливаем None (нет владельца)
    if owner_id:
        owner = db.query(User).filter(User.id == owner_id).first()
        if owner:
            task.owner_id = owner_id
        else:
            task.owner_id = None
    else:
        task.owner_id = None
    
    db.add(task)
    db.commit()
    
    return RedirectResponse(url="/admin/tasks?success=Задача обновлена", status_code=303)


@router.post("/tasks/{task_id}/delete")
def delete_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Удаляет задачу."""
    admin = check_admin(request)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/admin/tasks", status_code=303)
    
    db.delete(task)
    db.commit()
    
    return RedirectResponse(url="/admin/tasks?success=Задача удалена", status_code=303)

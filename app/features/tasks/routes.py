from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import uuid

from app.dependencies import get_db
from app.models import Task, User

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/tasks", response_class=HTMLResponse)
def list_tasks(request: Request, db: Session = Depends(get_db)):
    # show tasks list and simple create form
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": request.state.user})


@router.post("/tasks/create", response_class=HTMLResponse)
def create_task(request: Request, title: str = Form(...), description: str | None = Form(None), db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    task = Task(title=title, description=description, owner_id=user.id)
    db.add(task)
    db.commit()
    return RedirectResponse(url="/tasks", status_code=303)


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail(request: Request, task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)
    return templates.TemplateResponse("task_detail.html", {"request": request, "task": task, "user": request.state.user})


@router.post("/tasks/{task_id}/upload")
def upload_photo(request: Request, task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)

    # validate image
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    filename_raw = file.filename or f"{uuid.uuid4().hex}.jpg"
    ext = os.path.splitext(filename_raw)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(uploads_dir, filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    task.photo_path = f"/static/uploads/{filename}"
    db.add(task)
    db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)


@router.post("/tasks/{task_id}/delete")
def delete_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Delete task if current user is the owner. Also remove uploaded file if exists."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)

    if task.owner_id != user.id:
        # not allowed to delete others' tasks
        return RedirectResponse(url="/tasks", status_code=303)

    # remove photo file if present and inside uploads
    if task.photo_path:
        try:
            if task.photo_path.startswith("/static/uploads/"):
                file_path = task.photo_path.replace("/static/", "app/static/")
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception:
            # ignore file deletion errors
            pass

    db.delete(task)
    db.commit()
    return RedirectResponse(url="/tasks", status_code=303)

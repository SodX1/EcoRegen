from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import uuid

from app.dependencies import get_db
from app.models import Task, User
from app.image.ndvi import compute_ndvi
import json

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
    return RedirectResponse(url="/", status_code=303)


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
        return RedirectResponse(url="/", status_code=303)

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


@router.post("/tasks/{task_id}/ndvi")
def make_ndvi(request: Request, task_id: int, red_index: int = Form(0), nir_index: int = Form(3), db: Session = Depends(get_db)):
    """Compute NDVI for an uploaded photo. red_index and nir_index are 0-based channel indices."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)

    if task.owner_id != user.id:
        return RedirectResponse(url="/tasks", status_code=303)

    if not task.photo_path:
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    # map /static/... to filesystem path
    static_prefix = "/static/"
    if task.photo_path.startswith(static_prefix):
        file_path = task.photo_path.replace(static_prefix, "app/static/")
    else:
        file_path = task.photo_path

    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    # Use a stable filename per task so NDVI results are overwritten rather than creating many files
    ndvi_filename = f"ndvi_task_{task.id}.png"
    ndvi_path_fs = os.path.join(uploads_dir, ndvi_filename)
    ndvi_url = f"/static/uploads/{ndvi_filename}"

    ok = compute_ndvi(file_path, ndvi_path_fs, red_index=red_index, nir_index=nir_index)
    if ok:
        task.ndvi_path = ndvi_url
        task.ndvi_params = json.dumps({"red_index": red_index, "nir_index": nir_index})
        task.ndvi_error = None
        db.add(task)
        db.commit()
    else:
        # mark error and clear ndvi_path
        task.ndvi_error = f"NDVI не получилось для red={red_index}, nir={nir_index}"
        task.ndvi_path = None
        task.ndvi_params = json.dumps({"red_index": red_index, "nir_index": nir_index})
        db.add(task)
        db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)



@router.post("/tasks/{task_id}/segment")
def make_segmentation(request: Request, task_id: int, method: str = Form("yolo"), conf: float = Form(0.25), db: Session = Depends(get_db)):
    """Run segmentation on the uploaded photo for the task.

    method: 'yolo' or 'maskrcnn' (fallback will try both if 'yolo' fails)
    conf: confidence threshold (0..1)
    """
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)

    if task.owner_id != user.id:
        return RedirectResponse(url="/tasks", status_code=303)

    if not task.photo_path:
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    static_prefix = "/static/"
    if task.photo_path.startswith(static_prefix):
        file_path = task.photo_path.replace(static_prefix, "app/static/")
    else:
        file_path = task.photo_path

    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    seg_filename = f"segm_task_{task.id}.png"
    seg_path_fs = os.path.join(uploads_dir, seg_filename)
    seg_url = f"/static/uploads/{seg_filename}"

    # Try requested method; if yolo fails and method=='yolo' we'll fall back to maskrcnn inside utility
    from app.image.segmentation import run_segmentation

    ok, msg = run_segmentation(file_path, seg_path_fs, method=method, conf=float(conf))
    if ok:
        task.segmentation_path = seg_url
        task.segmentation_params = json.dumps({"method": method, "conf": float(conf)})
        task.segmentation_error = None
    else:
        task.segmentation_error = msg
        task.segmentation_path = None
        task.segmentation_params = json.dumps({"method": method, "conf": float(conf)})

    db.add(task)
    db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)


@router.post("/tasks/{task_id}/delete")
def delete_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Delete task if current user is the owner. Also remove uploaded file if exists."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/", status_code=303)

    if task.owner_id != user.id:
        # not allowed to delete others' tasks
        return RedirectResponse(url="/", status_code=303)

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
    return RedirectResponse(url="/", status_code=303)

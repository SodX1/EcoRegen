from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from typing import List
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import uuid
from datetime import datetime, timedelta

from app.dependencies import get_db
from app.models import Task, User, Photo, PhotoNDVI, PhotoAnalysis, PhotoSegmentation
from app.image.ndvi import compute_ndvi
from app.image.analysis import hsv_pixel_distribution
import traceback
import json

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/tasks", response_class=HTMLResponse)
def list_tasks(request: Request, db: Session = Depends(get_db), start_date: str | None = None, end_date: str | None = None):
    # show tasks list and simple create form with optional date filtering (YYYY-MM-DD)
    query = db.query(Task)
    try:
        if start_date:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Task.created_at >= sd)
        if end_date:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Task.created_at < ed)
    except Exception:
        # on parse error, ignore filters
        start_date = None
        end_date = None

    tasks = query.order_by(Task.created_at.desc()).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": request.state.user, "start_date": start_date, "end_date": end_date})


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
def upload_photo(request: Request, task_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/", status_code=303)
    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    saved = []
    for file in files:
        content_type = file.content_type or ""
        if not content_type.startswith("image/"):
            continue
        filename_raw = file.filename or f"{uuid.uuid4().hex}.jpg"
        ext = os.path.splitext(filename_raw)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(uploads_dir, filename)
        with open(path, "wb") as f:
            f.write(file.file.read())

        # create Photo record linked to the task
        from app.models import Photo
        # generate a default title like "Photo 1", "Photo 2"
        count = db.query(Photo).filter(Photo.task_id == task.id).count()
        title = f"Фото {count + 1}"
        photo = Photo(task_id=task.id, path=f"/static/uploads/{filename}", title=title)
        db.add(photo)
        saved.append(f"/static/uploads/{filename}")

    db.commit()
    # if task has no main photo_path yet, set the first uploaded as default
    if saved and not task.photo_path:
        task.photo_path = saved[0]
        db.add(task)
        db.commit()

    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)


@router.post("/tasks/{task_id}/ndvi")
def make_ndvi(request: Request, task_id: int, red_index: int = Form(0), nir_index: int = Form(3), photo_path: str | None = Form(None), db: Session = Depends(get_db)):
    """Compute NDVI for an uploaded photo. red_index and nir_index are 0-based channel indices."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)

    if task.owner_id != user.id:
        return RedirectResponse(url="/tasks", status_code=303)

    # resolve Photo: prefer photo_id if provided, otherwise try photo_path
    photo = None
    if isinstance(photo_path, str) and photo_path.isdigit():
        # edge-case where a numeric string was submitted as photo_path -> treat as id
        pid = int(photo_path)
        photo = db.query(Photo).filter(Photo.id == pid, Photo.task_id == task.id).first()

    # If form provided explicit photo_id (hidden input), try that
    # Some clients may post `photo_id` instead of `photo_path`.
    try:
        # try to read photo_id from form data if available
        if not photo:
            form = request.form()
            # note: request.form() returns an awaitable in Starlette; but FastAPI passes sync here. use safe approach below.
    except Exception:
        pass

    # Try to find by exact path match among photos
    if not photo and photo_path:
        photo = db.query(Photo).filter(Photo.path == photo_path, Photo.task_id == task.id).first()

    # fallback: if no photo resolved, try first photo of task
    if not photo:
        photo = db.query(Photo).filter(Photo.task_id == task.id).order_by(Photo.created_at.asc()).first()

    if not photo:
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    # map /static/... to filesystem path
    static_prefix = "/static/"
    if photo.path.startswith(static_prefix):
        file_path = photo.path.replace(static_prefix, "app/static/")
    else:
        file_path = photo.path

    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    # Use a stable filename per photo so NDVI results are stored per-photo
    ndvi_filename = f"ndvi_photo_{photo.id}.png"
    ndvi_path_fs = os.path.join(uploads_dir, ndvi_filename)
    ndvi_url = f"/static/uploads/{ndvi_filename}"

    ok = compute_ndvi(file_path, ndvi_path_fs, red_index=red_index, nir_index=nir_index)
    # Save results on the Photo level
    pnd = db.query(PhotoNDVI).filter(PhotoNDVI.photo_id == photo.id).first()
    if not pnd:
        pnd = PhotoNDVI(photo_id=photo.id)

    if ok:
        pnd.ndvi_path = ndvi_url
        pnd.ndvi_params = json.dumps({"red_index": red_index, "nir_index": nir_index})
        pnd.ndvi_error = None
    else:
        pnd.ndvi_error = f"NDVI не получилось для red={red_index}, nir={nir_index}"
        pnd.ndvi_path = None
        pnd.ndvi_params = json.dumps({"red_index": red_index, "nir_index": nir_index})

    db.add(pnd)
    try:
        db.commit()
    except Exception as e:
        # Try to recover from integrity issues (e.g. existing row with NULL photo_id)
        db.rollback()
        try:
            pnd.photo_id = photo.id
            db.add(pnd)
            db.commit()
        except Exception as e2:
            db.rollback()
            return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    # If AJAX/json client, return JSON with path/error
    accept = request.headers.get("accept", "")
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in accept:
        if pnd.ndvi_path:
            return JSONResponse({"success": True, "path": pnd.ndvi_path, "params": pnd.ndvi_params})
        else:
            return JSONResponse({"success": False, "error": pnd.ndvi_error, "params": pnd.ndvi_params}, status_code=400)

    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)



@router.post("/tasks/{task_id}/analyze_hsv")
def analyze_hsv(request: Request, task_id: int, hue_low: float = Form(35.0), hue_high: float = Form(85.0), sat_min: float = Form(0.2), val_min: float = Form(0.2), photo_path: str | None = Form(None), db: Session = Depends(get_db)):
    """Run HSV pixel analysis on the task photo and save pie chart."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse(url="/tasks", status_code=303)

    if task.owner_id != user.id:
        return RedirectResponse(url="/tasks", status_code=303)

    # resolve Photo: accept photo_id in photo_path field or full URL
    photo = None
    if isinstance(photo_path, str) and photo_path.isdigit():
        pid = int(photo_path)
        photo = db.query(Photo).filter(Photo.id == pid, Photo.task_id == task.id).first()

    if not photo and photo_path:
        photo = db.query(Photo).filter(Photo.path == photo_path, Photo.task_id == task.id).first()

    if not photo:
        photo = db.query(Photo).filter(Photo.task_id == task.id).order_by(Photo.created_at.asc()).first()

    if not photo:
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    static_prefix = "/static/"
    if photo.path.startswith(static_prefix):
        file_path = photo.path.replace(static_prefix, "app/static/")
    else:
        file_path = photo.path

    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    # Use a stable filename per photo so HSV analysis is kept per-photo
    analysis_filename = f"analysis_hsv_photo_{photo.id}.png"
    analysis_path_fs = os.path.join(uploads_dir, analysis_filename)
    analysis_url = f"/static/uploads/{analysis_filename}"

    # Ensure input file exists
    if not os.path.exists(file_path):
        pan = db.query(PhotoAnalysis).filter(PhotoAnalysis.photo_id == photo.id).first()
        if not pan:
            pan = PhotoAnalysis(photo_id=photo.id)
        pan.analysis_error = f"input file not found: {file_path}"
        pan.analysis_path = None
        pan.analysis_params = json.dumps({"method": "hsv", "hue_low": float(hue_low), "hue_high": float(hue_high), "sat_min": float(sat_min), "val_min": float(val_min)})
        db.add(pan)
        db.commit()
        accept = request.headers.get("accept", "")
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in accept:
            return JSONResponse({"success": False, "error": pan.analysis_error}, status_code=400)
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    try:
        ok, result = hsv_pixel_distribution(file_path, float(hue_low), float(hue_high), float(sat_min), float(val_min), analysis_path_fs)
    except Exception as e:
        tb = traceback.format_exc()
        ok = False
        result = f"exception: {e}\n{tb}"

    pan = db.query(PhotoAnalysis).filter(PhotoAnalysis.photo_id == photo.id).first()
    if not pan:
        pan = PhotoAnalysis(photo_id=photo.id)

    if ok:
        pan.analysis_path = analysis_url
        pan.analysis_params = json.dumps({"method": "hsv", "hue_low": float(hue_low), "hue_high": float(hue_high), "sat_min": float(sat_min), "val_min": float(val_min)})
        pan.analysis_error = None
    else:
        # result is either an error message or exception details
        pan.analysis_error = str(result)
        pan.analysis_path = None
        pan.analysis_params = json.dumps({"method": "hsv", "hue_low": float(hue_low), "hue_high": float(hue_high), "sat_min": float(sat_min), "val_min": float(val_min)})

    db.add(pan)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            pan.photo_id = photo.id
            db.add(pan)
            db.commit()
        except Exception:
            db.rollback()
            accept = request.headers.get("accept", "")
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in accept:
                return JSONResponse({"success": False, "error": "DB error saving analysis"}, status_code=500)
            return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    accept = request.headers.get("accept", "")
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in accept:
        if pan.analysis_path:
            return JSONResponse({"success": True, "path": pan.analysis_path, "params": pan.analysis_params})
        else:
            return JSONResponse({"success": False, "error": pan.analysis_error, "params": pan.analysis_params}, status_code=400)

    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)


@router.post("/tasks/{task_id}/photos/{photo_id}/rename")
def rename_photo(request: Request, task_id: int, photo_id: int, new_title: str = Form(...), db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return JSONResponse({"success": False, "error": "not_authenticated"}, status_code=403)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return JSONResponse({"success": False, "error": "not_found"}, status_code=404)

    if task.owner_id != user.id:
        return JSONResponse({"success": False, "error": "forbidden"}, status_code=403)

    from app.models import Photo
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.task_id == task_id).first()
    if not photo:
        return JSONResponse({"success": False, "error": "photo_not_found"}, status_code=404)

    photo.title = new_title or None
    db.add(photo)
    db.commit()
    return JSONResponse({"success": True, "photo_id": photo.id, "title": photo.title})



@router.post("/tasks/{task_id}/segment")
def make_segmentation(request: Request, task_id: int, method: str = Form("yolo"), conf: float = Form(0.25), photo_path: str | None = Form(None), db: Session = Depends(get_db)):
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

    # resolve Photo similar to other handlers
    photo = None
    if isinstance(photo_path, str) and photo_path.isdigit():
        pid = int(photo_path)
        photo = db.query(Photo).filter(Photo.id == pid, Photo.task_id == task.id).first()

    if not photo and photo_path:
        photo = db.query(Photo).filter(Photo.path == photo_path, Photo.task_id == task.id).first()

    if not photo:
        photo = db.query(Photo).filter(Photo.task_id == task.id).order_by(Photo.created_at.asc()).first()

    if not photo:
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    static_prefix = "/static/"
    if photo.path.startswith(static_prefix):
        file_path = photo.path.replace(static_prefix, "app/static/")
    else:
        file_path = photo.path

    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    seg_filename = f"segm_photo_{photo.id}.png"
    seg_path_fs = os.path.join(uploads_dir, seg_filename)
    seg_url = f"/static/uploads/{seg_filename}"

    # Try requested method; if yolo fails and method=='yolo' we'll fall back to maskrcnn inside utility
    from app.image.segmentation import run_segmentation

    ok, msg = run_segmentation(file_path, seg_path_fs, method=method, conf=float(conf))
    pseg = db.query(PhotoSegmentation).filter(PhotoSegmentation.photo_id == photo.id).first()
    if not pseg:
        pseg = PhotoSegmentation(photo_id=photo.id)

    if ok:
        pseg.segmentation_path = seg_url
        pseg.segmentation_params = json.dumps({"method": method, "conf": float(conf)})
        pseg.segmentation_error = None
    else:
        pseg.segmentation_error = msg
        pseg.segmentation_path = None
        pseg.segmentation_params = json.dumps({"method": method, "conf": float(conf)})

    db.add(pseg)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            pseg.photo_id = photo.id
            db.add(pseg)
            db.commit()
        except Exception:
            db.rollback()
            return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    accept = request.headers.get("accept", "")
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in accept:
        if pseg.segmentation_path:
            return JSONResponse({"success": True, "path": pseg.segmentation_path, "params": pseg.segmentation_params})
        else:
            return JSONResponse({"success": False, "error": pseg.segmentation_error, "params": pseg.segmentation_params}, status_code=400)

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
    # remove each photo file and any generated artifacts (ndvi/analysis/segmentation)
    try:
        from app.models import Photo
        for photo in list(task.photos or []):
            try:
                # original uploaded photo
                if photo.path and photo.path.startswith("/static/uploads/"):
                    pfs = photo.path.replace("/static/", "app/static/")
                    if os.path.exists(pfs):
                        os.remove(pfs)
                # generated NDVI image
                ndvi_file = os.path.join("app", "static", "uploads", f"ndvi_photo_{photo.id}.png")
                if os.path.exists(ndvi_file):
                    os.remove(ndvi_file)
                # generated HSV analysis image
                hsv_file = os.path.join("app", "static", "uploads", f"analysis_hsv_photo_{photo.id}.png")
                if os.path.exists(hsv_file):
                    os.remove(hsv_file)
                # segmentation image
                seg_file = os.path.join("app", "static", "uploads", f"segm_photo_{photo.id}.png")
                if os.path.exists(seg_file):
                    os.remove(seg_file)
            except Exception:
                # ignore per-file deletion errors
                pass
    except Exception:
        pass

    db.delete(task)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

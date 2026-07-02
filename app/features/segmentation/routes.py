from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import io
from pathlib import Path
import json
import base64

from app.image.segmentation_model import SegmentationModel
from app.tasks import segment_image

router = APIRouter(prefix="/api/segment", tags=["segmentation"])


@router.post("/predict")
async def predict_segmentation(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    iou: float = Query(0.45, ge=0.0, le=1.0),
):
    """Run YOLOv8 segmentation on uploaded image."""
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    try:
        model = SegmentationModel.get_instance()
        result = model.predict(image, conf=conf, iou=iou)
        return JSONResponse(result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@router.get("/health")
async def health():
    """Check if model is loaded and ready."""
    try:
        model = SegmentationModel.get_instance()
        return {
            "status": "ok",
            "model": str(model.weights_path),
            "device": model.device,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/predict-image")
async def predict_image(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    iou: float = Query(0.45, ge=0.0, le=1.0),
    format: str = Query("png", regex="^(png|jpeg|jpg)$"),
):
    """Run YOLOv8 segmentation and return image with drawn masks (PNG/JPEG)."""
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    try:
        model = SegmentationModel.get_instance()
        vis_image, result = model.predict_and_visualize(image, conf=conf, iou=iou)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img_format = "PNG" if format == "png" else "JPEG"
        vis_image.save(img_buffer, format=img_format, quality=95 if format != "png" else None)
        img_buffer.seek(0)
        
        media_type = "image/png" if format == "png" else "image/jpeg"
        return StreamingResponse(img_buffer, media_type=media_type)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@router.post("/predict-json")
async def predict_json(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    iou: float = Query(0.45, ge=0.0, le=1.0),
):
    """Run YOLOv8 segmentation and return JSON with detection metadata."""
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    try:
        model = SegmentationModel.get_instance()
        vis_image, result = model.predict_and_visualize(image, conf=conf, iou=iou)
        return JSONResponse(result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@router.post("/async-predict")
async def async_predict(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    iou: float = Query(0.45, ge=0.0, le=1.0),
    return_image: bool = Query(True),
):
    """
    Запустить асинхронное предсказание (без блокировки).
    Возвращает task_id для отслеживания прогресса.
    """
    try:
        image_data = await file.read()
        image_b64 = base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    try:
        # Запустить асинхронную задачу
        task = segment_image.delay(image_b64, conf=conf, iou=iou, return_image=return_image)
        return {
            "task_id": task.id,
            "status": "queued",
            "message": "Task queued for processing",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Получить статус и результат задачи по ID."""
    try:
        task = segment_image.AsyncResult(task_id)
        
        if task.state == "PENDING":
            return {
                "task_id": task_id,
                "status": "pending",
                "progress": 0,
            }
        elif task.state == "PROCESSING":
            return {
                "task_id": task_id,
                "status": "processing",
                "progress": task.info.get("progress", 0),
            }
        elif task.state == "SUCCESS":
            return {
                "task_id": task_id,
                "status": "success",
                "result": task.result,
            }
        elif task.state == "FAILURE":
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(task.info),
            }
        else:
            return {
                "task_id": task_id,
                "status": task.state.lower(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting task status: {str(e)}")

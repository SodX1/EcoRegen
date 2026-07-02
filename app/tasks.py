from __future__ import annotations

import io
import json
import base64
from pathlib import Path
from PIL import Image

from app.celery_app import app
from app.image.segmentation_model import SegmentationModel


@app.task(bind=True, name="app.tasks.segment_image")
def segment_image(
    self,
    image_base64: str,
    conf: float = 0.25,
    iou: float = 0.45,
    return_image: bool = True,
) -> dict:
    """
    Асинхронная задача для сегментации изображения.
    
    Args:
        image_base64: Изображение в формате base64
        conf: Порог уверенности
        iou: IoU порог для NMS
        return_image: Возвращать ли визуализированное изображение
    
    Returns:
        Словарь с результатами и опционально изображением в base64
    """
    try:
        self.update_state(state="PROCESSING", meta={"progress": 10})
        
        # Декодировать изображение из base64
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        self.update_state(state="PROCESSING", meta={"progress": 30})
        
        # Загрузить модель
        model = SegmentationModel.get_instance()
        
        self.update_state(state="PROCESSING", meta={"progress": 50})
        
        # Запустить inference с визуализацией
        vis_image, result = model.predict_and_visualize(image, conf=conf, iou=iou)
        
        self.update_state(state="PROCESSING", meta={"progress": 80})
        
        # Кодировать результирующее изображение в base64
        if return_image:
            img_buffer = io.BytesIO()
            vis_image.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            image_b64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
            result["image_png"] = image_b64
            result["image_url"] = f"data:image/png;base64,{image_b64}"
        
        self.update_state(state="PROCESSING", meta={"progress": 100})
        
        return {
            "status": "success",
            "data": result,
        }
    
    except FileNotFoundError as e:
        return {
            "status": "error",
            "error": f"Model not found: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Inference error: {str(e)}",
        }

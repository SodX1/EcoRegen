from PIL import Image
import numpy as np
import os
from typing import Tuple
from ultralytics import YOLO # type: ignore

def run_segmentation(input_path: str, output_path: str, method: str = "yolo", conf: float = 0.25) -> Tuple[bool, str]:
    """Attempt segmentation/instance annotation on input image and save annotated image to output_path.

    - method: "yolo" (try ultralytics YOLO segmentation) or "maskrcnn" (torchvision Mask R-CNN fallback)
    - conf: confidence threshold

    Returns: (success: bool, message: str). On success message is empty string.
    """
    # Try ultralytics YOLO (segmentation) if requested
    if method == "yolo":
        try:
            # import here so dependency is optional
            
            # try to load a small segmentation model by name; weight will be downloaded if missing
            model = YOLO("yolov8n-seg")
            results = model.predict(source=input_path, imgsz=640, conf=conf, verbose=False)
            if len(results) == 0:
                return False, "YOLO вернул пустые результаты"
            res = results[0]
            # res.plot() returns an image array with annotations
            try:
                arr = res.plot(boxes=False, masks=True)  # show masks only, no boxes
                img = Image.fromarray(arr)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                img.save(output_path)
                return True, ""
            except Exception as e:
                return False, f"YOLO: не удалось сохранить результат: {e}"
        except Exception as e:
            # return error to indicate ultralytics not available or failed
            return False, f"YOLO error: {e}"

    # Fallback to torchvision Mask R-CNN (instance segmentation -> draw masks)
    try:
        import torch
        from torchvision import transforms
        from torchvision.models.detection import (
            MaskRCNN_ResNet50_FPN_Weights,
            maskrcnn_resnet50_fpn_v2,
            maskrcnn_resnet50_fpn
        )

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
        model = maskrcnn_resnet50_fpn(weights=weights).to(device)
        model.eval()

        pil = Image.open(input_path).convert("RGB")
        transform = weights.transforms()
        img_t = transform(pil).to(device)

        with torch.no_grad():
            outputs = model([img_t])

        output = outputs[0]
        scores = output["scores"].cpu().numpy()
        masks = output.get("masks")

        base = np.array(pil).astype(np.uint8)

        # draw top detections above confidence
        if scores.size == 0 or masks is None or len(masks) == 0:
            return False, "Mask R-CNN: модель не нашла масок"
        keep_idx = np.where(scores >= conf)[0]
        if len(keep_idx) == 0:
            # Fallback to a softer threshold or the top detection
            soft_idx = np.where(scores >= 0.05)[0]
            if len(soft_idx) == 0:
                soft_idx = np.array([int(np.argmax(scores))])
            keep_idx = soft_idx[:3]

        overlay = base.copy()
        alpha = 0.35
        for i in keep_idx:
            if masks is None:
                continue
            mask = masks[i, 0].cpu().numpy()
            mask_bool = mask >= 0.5
            color = np.array([38, 166, 91], dtype=np.uint8)
            overlay[mask_bool] = (overlay[mask_bool] * (1 - alpha) + color * alpha).astype(np.uint8)

        out_img = Image.fromarray(overlay)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out_img.save(output_path)
        return True, ""
    except Exception as e:
        return False, f"MaskRCNN error: {e}"
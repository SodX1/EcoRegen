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
                arr = res.plot()
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
        from torchvision.models.detection import maskrcnn_resnet50_fpn

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = maskrcnn_resnet50_fpn(pretrained=True).to(device)
        model.eval()

        pil = Image.open(input_path).convert("RGB")
        transform = transforms.Compose([transforms.ToTensor()])
        img_t = transform(pil).to(device)

        with torch.no_grad():
            outputs = model([img_t])

        output = outputs[0]
        scores = output["scores"].cpu().numpy()
        boxes = output["boxes"].cpu().numpy()
        masks = output.get("masks")

        h, w = pil.size[1], pil.size[0]
        base = np.array(pil).astype(np.uint8)

        # draw top detections above confidence
        keep_idx = np.where(scores >= conf)[0]
        if len(keep_idx) == 0:
            return False, "Mask R-CNN: нет объектов выше порога"

        overlay = base.copy()
        alpha = 0.5
        for i in keep_idx:
            if masks is None:
                continue
            mask = masks[i, 0].cpu().numpy()
            mask_bool = mask >= 0.5
            color = np.random.randint(0, 255, size=(3,), dtype=np.uint8)
            overlay[mask_bool] = (overlay[mask_bool] * (1 - alpha) + color * alpha).astype(np.uint8)

        out_img = Image.fromarray(overlay)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out_img.save(output_path)
        return True, ""
    except Exception as e:
        return False, f"MaskRCNN error: {e}"

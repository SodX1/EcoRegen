from __future__ import annotations

from pathlib import Path
from typing import Optional
import torch
from PIL import Image, ImageDraw
import io
import base64
import numpy as np


class SegmentationModel:
    """Wrapper for YOLOv8 segmentation model inference."""

    _instance = None

    def __init__(self, weights_path: str | Path | None = None, device: str | None = None):
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError("ultralytics package required. Install via: pip install ultralytics")

        if weights_path is None:
            # Try to find best.pt from training run
            project_root = Path(".").resolve()
            weights_path = project_root / "yolov8_seg_run" / "weights" / "best.pt"
            if not weights_path.exists():
                raise FileNotFoundError(f"Model weights not found: {weights_path}")

        self.weights_path = Path(weights_path)
        if not self.weights_path.exists():
            raise FileNotFoundError(f"Model weights not found: {self.weights_path}")

        if device is None:
            device = "0" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.model = YOLO(str(self.weights_path))
        print(f"[SegmentationModel] Loaded from {self.weights_path} on device {device}")

    @classmethod
    def get_instance(cls, weights_path: str | Path | None = None, device: str | None = None) -> SegmentationModel:
        """Lazy-load singleton instance."""
        if cls._instance is None:
            cls._instance = cls(weights_path=weights_path, device=device)
        return cls._instance

    def predict(
        self,
        image_pil: Image.Image,
        conf: float = 0.25,
        iou: float = 0.45,
    ) -> dict:
        """Run inference on a PIL Image and return results."""
        results = self.model.predict(
            source=image_pil,
            device=self.device,
            conf=conf,
            iou=iou,
            verbose=False,
        )

        result = results[0]
        output = {
            "detections": [],
            "image_shape": result.orig_shape,
            "model": str(self.weights_path.name),
        }

        if result.masks is not None:
            for idx, (mask, box, cls_id, conf) in enumerate(
                zip(
                    result.masks.data,
                    result.boxes.xyxy,
                    result.boxes.cls,
                    result.boxes.conf,
                )
            ):
                output["detections"].append({
                    "id": idx,
                    "class": int(cls_id.item()),
                    "confidence": float(conf.item()),
                    "bbox": [float(v) for v in box.tolist()],
                    "mask_shape": [int(mask.shape[0]), int(mask.shape[1])],
                })

        return output

    def predict_file(
        self,
        image_path: str | Path,
        conf: float = 0.25,
        iou: float = 0.45,
    ) -> dict:
        """Run inference on image file."""
        image = Image.open(image_path).convert("RGB")
        return self.predict(image, conf=conf, iou=iou)

    def predict_and_visualize(
        self,
        image_pil: Image.Image,
        conf: float = 0.25,
        iou: float = 0.45,
        thickness: int = 2,
        alpha: float = 0.3,
    ) -> tuple[Image.Image, dict]:
        """Run inference and return image with drawn masks + detection results."""
        results = self.model.predict(
            source=image_pil,
            device=self.device,
            conf=conf,
            iou=iou,
            verbose=False,
        )

        result = results[0]
        vis_image = image_pil.copy()
        draw = ImageDraw.Draw(vis_image, 'RGBA')

        output = {
            "detections": [],
            "image_shape": result.orig_shape,
            "model": str(self.weights_path.name),
        }

        if result.masks is not None:
            for idx, (mask, box, cls_id, conf) in enumerate(
                zip(
                    result.masks.data,
                    result.boxes.xyxy,
                    result.boxes.cls,
                    result.boxes.conf,
                )
            ):
                # Convert mask to numpy and get contours/polygon
                mask_np = mask.cpu().numpy().astype(np.uint8)
                
                # Draw mask on image with transparency
                mask_rgb = np.zeros((*mask_np.shape, 4), dtype=np.uint8)
                # Green for oil (class 1), red for no-oil (class 0)
                cls_int = int(cls_id.item())
                if cls_int == 1:  # oil
                    mask_rgb[mask_np > 0] = [0, 255, 0, int(255 * alpha)]
                else:
                    mask_rgb[mask_np > 0] = [255, 0, 0, int(255 * alpha)]
                
                mask_img = Image.fromarray(mask_rgb)
                vis_image.paste(mask_img, (0, 0), mask_img)

                # Draw bounding box
                box_coords = box.tolist()
                draw.rectangle(
                    [(box_coords[0], box_coords[1]), (box_coords[2], box_coords[3])],
                    outline=(0, 255, 0) if cls_int == 1 else (255, 0, 0),
                    width=thickness,
                )

                # Draw label
                label = f"{'Oil' if cls_int == 1 else 'NoOil'} {conf.item():.2f}"
                draw.text((box_coords[0], box_coords[1] - 10), label, fill=(255, 255, 255))

                output["detections"].append({
                    "id": idx,
                    "class": cls_int,
                    "class_name": "oil" if cls_int == 1 else "no_oil",
                    "confidence": float(conf.item()),
                    "bbox": box_coords,
                    "mask_shape": [int(mask_np.shape[0]), int(mask_np.shape[1])],
                })

        return vis_image, output

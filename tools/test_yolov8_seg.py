from __future__ import annotations

from pathlib import Path
import argparse
import torch
import json


def test(args: argparse.Namespace) -> None:
    try:
        from ultralytics import YOLO
    except Exception as e:
        raise SystemExit("ultralytics package is required. Install via `pip install ultralytics`")

    project_root = Path(args.project_root).resolve()
    weights = Path(args.weights).resolve() if args.weights else project_root / "yolov8_seg_run" / "weights" / "best.pt"
    
    if not weights.exists():
        print(f"Model weights not found: {weights}")
        print("Available weights might be at:")
        for p in (project_root / "yolov8_seg_run" / "weights").glob("*.pt"):
            print(f"  - {p}")
        raise SystemExit("Specify --weights path")

    print(f"Loading model from {weights}")
    model = YOLO(str(weights))

    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    test_dir = project_root / "dataset" / "test" / "images"
    if not test_dir.exists():
        raise SystemExit(f"Test images directory not found: {test_dir}")

    print(f"\nRunning inference on {test_dir}")
    results = model.predict(
        source=str(test_dir),
        device=device,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        save=True,
        project=str(project_root),
        name="test_results",
        exist_ok=True,
    )

    print(f"\nInference complete. Results saved to test_results/")
    print(f"Number of images processed: {len(results)}")

    # Summary stats
    total_detections = 0
    for r in results:
        if r.masks is not None:
            total_detections += len(r.masks)

    print(f"Total segmentations detected: {total_detections}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test YOLOv8 segmentation model")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--weights", default=None, help="Path to .pt weights file (default: yolov8_seg_run/weights/best.pt)")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold for NMS")
    return parser.parse_args()


if __name__ == "__main__":
    test(parse_args())

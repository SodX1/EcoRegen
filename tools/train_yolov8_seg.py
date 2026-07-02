from __future__ import annotations

from pathlib import Path
import argparse
import torch

def train(args: argparse.Namespace) -> None:
    try:
        from ultralytics import YOLO
    except Exception as e:
        raise SystemExit("ultralytics package is required. Install via `pip install ultralytics`")

    weights = args.weights or "yolov8n-seg.pt"
    model = YOLO(weights)

    # choose device: explicit arg wins, otherwise use GPU if available
    if args.device is None:
        device = "0" if torch.cuda.is_available() else "cpu"
    else:
        # allow numeric device ids
        device = str(args.device)

    print(f"Starting YOLOv8 segmentation training: weights={weights} device={device}")
    model.train(
        data=str(Path(args.project_root) / "dataset" / "data.yaml"),
        epochs=args.epochs,
        batch=args.batch_size,
        imgsz=args.imgsz,
        device=device,
        project=args.project_root,
        name=args.name,
        exist_ok=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLOv8 segmentation on prepared dataset")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--weights", default=None, help="Weights file path or model name")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default=None, help="Device id like 0 or 'cpu'")
    parser.add_argument("--name", default="yolov8_seg_run")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())

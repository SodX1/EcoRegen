import argparse
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import yaml
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.transforms import functional as F


def collate_fn(batch):
    return tuple(zip(*batch))


def yolo_poly_to_mask(points: list[float], width: int, height: int) -> np.ndarray:
    pts = np.array(points, dtype=np.float32).reshape(-1, 2)
    pts[:, 0] = np.clip(pts[:, 0] * width, 0, width - 1)
    pts[:, 1] = np.clip(pts[:, 1] * height, 0, height - 1)
    pts_int = pts.astype(np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    if len(pts_int) >= 3:
        cv2.fillPoly(mask, [pts_int], 1)
    return mask


class YoloSegMaskDataset(Dataset):
    def __init__(self, images_dir: Path, labels_dir: Path, oil_class_ids: set[int]):
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.oil_class_ids = oil_class_ids
        self.image_files = sorted(
            [
                p
                for p in images_dir.glob("*")
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
            ]
        )

    def __len__(self) -> int:
        return len(self.image_files)

    def __getitem__(self, idx: int):
        img_path = self.image_files[idx]
        label_path = self.labels_dir / f"{img_path.stem}.txt"

        pil = Image.open(img_path).convert("RGB")
        image = F.to_tensor(pil)
        width, height = pil.size

        masks = []
        boxes = []
        labels = []

        if label_path.exists():
            lines = label_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) < 7:
                    continue
                try:
                    class_id = int(float(parts[0]))
                    if class_id not in self.oil_class_ids:
                        continue
                    coords = [float(v) for v in parts[1:]]
                except ValueError:
                    continue

                if len(coords) < 6 or len(coords) % 2 != 0:
                    continue

                mask = yolo_poly_to_mask(coords, width, height)
                ys, xs = np.where(mask > 0)
                if len(xs) == 0 or len(ys) == 0:
                    continue

                x_min, x_max = float(xs.min()), float(xs.max())
                y_min, y_max = float(ys.min()), float(ys.max())
                if x_max <= x_min or y_max <= y_min:
                    continue

                masks.append(mask)
                boxes.append([x_min, y_min, x_max, y_max])
                labels.append(1)

        if len(masks) == 0:
            masks_t = torch.zeros((0, height, width), dtype=torch.uint8)
            boxes_t = torch.zeros((0, 4), dtype=torch.float32)
            labels_t = torch.zeros((0,), dtype=torch.int64)
            area_t = torch.zeros((0,), dtype=torch.float32)
            iscrowd_t = torch.zeros((0,), dtype=torch.int64)
        else:
            masks_t = torch.as_tensor(np.stack(masks), dtype=torch.uint8)
            boxes_t = torch.as_tensor(boxes, dtype=torch.float32)
            labels_t = torch.as_tensor(labels, dtype=torch.int64)
            area_t = (boxes_t[:, 3] - boxes_t[:, 1]) * (boxes_t[:, 2] - boxes_t[:, 0])
            iscrowd_t = torch.zeros((len(masks),), dtype=torch.int64)

        target = {
            "boxes": boxes_t,
            "labels": labels_t,
            "masks": masks_t,
            "image_id": torch.tensor([idx]),
            "area": area_t,
            "iscrowd": iscrowd_t,
        }
        return image, target


def build_model(num_classes: int = 2):
    model = maskrcnn_resnet50_fpn(weights="DEFAULT")

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256
    model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)
    return model


def get_oil_class_ids(data_yaml: dict[str, Any]) -> set[int]:
    names = data_yaml.get("names", [])
    oil_ids: set[int] = set()

    for idx, name in enumerate(names):
        n = str(name).lower()
        if "oil" in n or "нефт" in n or "spill" in n:
            oil_ids.add(idx)

    if not oil_ids:
        # fallback: use all classes as positive spill masks
        oil_ids = set(range(int(data_yaml.get("nc", len(names) or 1))))

    return oil_ids


def train(args: argparse.Namespace) -> None:
    root = Path(args.project_root).resolve()
    data_yaml_path = root / "dataset" / "data.yaml"
    data = yaml.safe_load(data_yaml_path.read_text(encoding="utf-8"))

    oil_class_ids = get_oil_class_ids(data)
    print(f"Oil class ids used for training: {sorted(oil_class_ids)}")

    train_images = root / "dataset" / "train" / "images"
    train_labels = root / "dataset" / "train" / "labels"
    val_images = root / "dataset" / "valid" / "images"
    val_labels = root / "dataset" / "valid" / "labels"

    ds_train = YoloSegMaskDataset(train_images, train_labels, oil_class_ids)
    ds_val = YoloSegMaskDataset(val_images, val_labels, oil_class_ids)

    dl_train = DataLoader(
        ds_train,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_fn,
        pin_memory=torch.cuda.is_available(),
    )
    dl_val = DataLoader(
        ds_val,
        batch_size=1,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=collate_fn,
        pin_memory=torch.cuda.is_available(),
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(num_classes=2).to(device)

    optimizer = torch.optim.SGD(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr,
        momentum=0.9,
        weight_decay=0.0005,
    )
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    out_path = root / "app" / "models"
    out_path.mkdir(parents=True, exist_ok=True)
    best_ckpt = out_path / "maskrcnn_oilspill_best.pth"
    last_ckpt = out_path / "maskrcnn_oilspill_last.pth"

    scaler = torch.amp.GradScaler("cuda", enabled=torch.cuda.is_available())
    best_val_loss = float("inf")

    for epoch in range(args.epochs):
        model.train()
        running_train = 0.0

        for images, targets in dl_train:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=torch.cuda.is_available()):
                loss_dict = model(images, targets)
                loss = sum(loss_dict.values())

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running_train += float(loss.item())

        model.train()
        running_val = 0.0
        with torch.no_grad():
            for images, targets in dl_val:
                images = [img.to(device) for img in images]
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                loss_dict = model(images, targets)
                loss = sum(loss_dict.values())
                running_val += float(loss.item())

        train_loss = running_train / max(1, len(dl_train))
        val_loss = running_val / max(1, len(dl_val))
        print(f"Epoch {epoch + 1}/{args.epochs} | train_loss={train_loss:.4f} | val_loss={val_loss:.4f}")

        torch.save(
            {
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
            },
            last_ckpt,
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({"model_state_dict": model.state_dict(), "val_loss": val_loss}, best_ckpt)
            print(f"  -> saved new best checkpoint: {best_ckpt}")

        scheduler.step()

    print(f"Training finished. Best val_loss={best_val_loss:.4f}")
    print(f"Best checkpoint: {best_ckpt}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune Mask R-CNN for oil-spill segmentation")
    parser.add_argument("--project-root", default=".", help="Path to project root")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=0.005)
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
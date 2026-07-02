from __future__ import annotations

from pathlib import Path
import shutil
import random


def detect_class_from_name(name: str) -> int | None:
    idx = name.rfind("_cls_")
    if idx != -1:
        try:
            return int(name[idx + 5 : idx + 6])
        except Exception:
            return None
    if "/Class_1" in name or "\\Class_1" in name or "/1/" in name or "\\1\\" in name:
        return 1
    if "/Class_0" in name or "\\Class_0" in name or "/0/" in name or "\\0\\" in name:
        return 0
    return None


def write_polygon_label(path: Path, class_id: int | None) -> None:
    if class_id is None or class_id == 0:
        path.write_text("", encoding="utf-8")
        return
    coords = "0.0 0.0 1.0 0.0 1.0 1.0 0.0 1.0"
    path.write_text(f"{class_id} {coords}\n", encoding="utf-8")


def prepare(project_root: Path, out_root: Path, val_frac: float = 0.1, test_frac: float = 0.1) -> None:
    src = project_root / "data2" / "data"
    if not src.exists():
        raise SystemExit(f"Source data folder not found: {src}")
    images = [p for p in src.rglob("*.jpg")] + [p for p in src.rglob("*.png")]
    images = sorted(images)
    random.shuffle(images)
    n = len(images)
    ni = int(n * (1 - val_frac - test_frac))
    nv = int(n * val_frac)
    splits = {
        "train": images[:ni],
        "val": images[ni : ni + nv],
        "test": images[ni + nv :],
    }
    ds_root = out_root / "dataset"
    for split, files in splits.items():
        img_dir = ds_root / split / "images"
        lbl_dir = ds_root / split / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)
        for src_img in files:
            dst_img = img_dir / src_img.name
            shutil.copy2(src_img, dst_img)
            class_id = detect_class_from_name(str(src_img))
            lbl_file = lbl_dir / f"{src_img.stem}.txt"
            write_polygon_label(lbl_file, class_id)
    data_yaml = ds_root / "data.yaml"
    # YOLO expects paths relative to the data.yaml location when using a local dataset folder.
    content = "\n".join([
        "train: train/images",
        "val: val/images",
        "test: test/images",
        "",
        "nc: 2",
        "names: ['no_oil','oil']",
    ]) + "\n"
    data_yaml.write_text(content, encoding="utf-8")


def main() -> None:
    project_root = Path(".").resolve()
    out_root = project_root
    print("Preparing dataset from data2 into ./dataset ...")
    prepare(project_root, out_root)
    print("Done. dataset/ created with train/val/test splits and labels.")


if __name__ == "__main__":
    main()

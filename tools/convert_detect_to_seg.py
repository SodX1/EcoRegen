from __future__ import annotations

from pathlib import Path


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def bbox_to_polygon(xc: float, yc: float, w: float, h: float) -> list[float]:
    x1 = clamp01(xc - w / 2)
    y1 = clamp01(yc - h / 2)
    x2 = clamp01(xc + w / 2)
    y2 = clamp01(yc - h / 2)
    x3 = clamp01(xc + w / 2)
    y3 = clamp01(yc + h / 2)
    x4 = clamp01(xc - w / 2)
    y4 = clamp01(yc + h / 2)
    return [x1, y1, x2, y2, x3, y3, x4, y4]


def convert_label_file(path: Path) -> tuple[int, int]:
    converted = 0
    kept = 0
    out_lines: list[str] = []

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return 0, 0

    for raw in text.splitlines():
        parts = raw.strip().split()
        if not parts:
            continue

        if len(parts) == 5:
            cls = int(float(parts[0]))
            xc, yc, w, h = map(float, parts[1:])
            poly = bbox_to_polygon(xc, yc, w, h)
            out_lines.append("{} {}".format(cls, " ".join(f"{v:.6f}" for v in poly)))
            converted += 1
        else:
            out_lines.append(raw.strip())
            kept += 1

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return converted, kept


def main() -> None:
    root = Path("dataset")
    label_dirs = [root / "train" / "labels", root / "valid" / "labels", root / "test" / "labels"]

    total_files = 0
    total_converted = 0
    total_kept = 0

    for label_dir in label_dirs:
        if not label_dir.exists():
            continue
        for label_file in label_dir.glob("*.txt"):
            converted, kept = convert_label_file(label_file)
            total_files += 1
            total_converted += converted
            total_kept += kept

    print(f"files={total_files}")
    print(f"converted_rows={total_converted}")
    print(f"kept_rows={total_kept}")


if __name__ == "__main__":
    main()

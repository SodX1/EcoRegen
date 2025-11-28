from PIL import Image
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Tuple, Union

from .ndvi import compute_ndvi_array


def analyze_ndvi_pixel_distribution(input_path: str, red_index: int, nir_index: int, bins: Tuple[float, float], output_path: str) -> Tuple[bool, Union[Dict[str, float], str]]:
    try:
        ndvi = compute_ndvi_array(input_path, red_index=red_index, nir_index=nir_index)
    except Exception as e:
        return False, f"NDVI computation failed: {e}"

    t0, t1 = bins
    if not (-1.0 <= t0 < t1 <= 1.0):
        return False, "Неверные пороги (ожидается: -1 <= t0 < t1 <= 1)"

    total = ndvi.size
    low_mask = ndvi < t0
    mid_mask = (ndvi >= t0) & (ndvi < t1)
    high_mask = ndvi >= t1

    low_count = int(np.count_nonzero(low_mask))
    mid_count = int(np.count_nonzero(mid_mask))
    high_count = int(np.count_nonzero(high_mask))

    counted = low_count + mid_count + high_count
    other = total - counted if counted != total else 0

    dist = {
        "low": low_count / total,
        "mid": mid_count / total,
        "high": high_count / total,
    }
    if other > 0:
        dist["other"] = other / total

    labels = []
    sizes = []
    for k, v in dist.items():
        labels.append(f"{k} ({v*100:.1f}%)")
        sizes.append(v)

    try:
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(sizes, labels=labels, autopct=None, startangle=90)
        ax.axis('equal')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, bbox_inches='tight')
        plt.close(fig)
        return True, dist
    except Exception as e:
        return False, f"Ошибка при построении диаграммы: {e}"


def hsv_pixel_distribution(input_path: str, hue_low: float, hue_high: float, sat_min: float, val_min: float, output_path: str) -> Tuple[bool, Union[Dict[str, float], str]]:
    try:
        img = Image.open(input_path).convert('RGB')
        arr = np.array(img).astype('uint8')
    except Exception as e:
        return False, f"Не удалось открыть изображение: {e}"

    # Try OpenCV first for speed
    try:
        import cv2
        bgr = arr[:, :, ::-1]
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype('float32')
        h = hsv[:, :, 0] * 2.0  # 0..360
        s = hsv[:, :, 1] / 255.0
        v = hsv[:, :, 2] / 255.0
    except Exception:
        # fallback to colorsys (slower)
        try:
            import colorsys
            h = np.zeros(arr.shape[:2], dtype=float)
            s = np.zeros(arr.shape[:2], dtype=float)
            v = np.zeros(arr.shape[:2], dtype=float)
            norm = arr / 255.0
            rows, cols = arr.shape[:2]
            for i in range(rows):
                for j in range(cols):
                    r, g, b = norm[i, j]
                    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
                    h[i, j] = hh * 360.0
                    s[i, j] = ss
                    v[i, j] = vv
        except Exception as e:
            return False, f"Ошибка при конвертации в HSV: {e}"

    # hue range support across 360 boundary
    if hue_low <= hue_high:
        hue_mask = (h >= hue_low) & (h < hue_high)
    else:
        hue_mask = (h >= hue_low) | (h < hue_high)

    sat_mask = s >= sat_min
    val_mask = v >= val_min

    match_mask = hue_mask & sat_mask & val_mask
    total = match_mask.size
    match_count = int(np.count_nonzero(match_mask))
    other_count = int(total - match_count)

    dist = {"match": match_count / total, "other": other_count / total}

    labels = [f"match ({dist['match']*100:.1f}%)", f"other ({dist['other']*100:.1f}%)"]
    sizes = [dist['match'], dist['other']]
    try:
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(sizes, labels=labels, startangle=90)
        ax.axis('equal')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, bbox_inches='tight')
        plt.close(fig)
        return True, dist
    except Exception as e:
        return False, f"Ошибка при построении диаграммы: {e}"

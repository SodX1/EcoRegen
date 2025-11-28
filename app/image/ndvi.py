from PIL import Image
import numpy as np
import os

def compute_ndvi(input_path: str, output_path: str, red_index: int = 0, nir_index: int = 3) -> bool:
    """Compute a simple NDVI image from input image and save visualization to output_path.

    - input_path: filesystem path to image
    - output_path: filesystem path where visualization PNG will be saved
    - red_index, nir_index: integer channel indices (0-based) to use for Red and NIR bands

    Returns True on success, False on failure.
    """
    try:
        ndvi = compute_ndvi_array(input_path, red_index=red_index, nir_index=nir_index)

        # normalize to 0..1 for visualization
        ndvi_norm = (ndvi + 1.0) / 2.0

        # simple color mapping: R = (1-ndvi)*255, G = ndvi*255, B = 0
        r = ((1.0 - ndvi_norm) * 255.0).astype(np.uint8)
        g = (ndvi_norm * 255.0).astype(np.uint8)
        b = np.zeros_like(r, dtype=np.uint8)

        rgb = np.stack([r, g, b], axis=-1)
        out_img = Image.fromarray(rgb)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out_img.save(output_path, format="PNG")
        return True
    except Exception:
        return False


def compute_ndvi_array(input_path: str, red_index: int = 0, nir_index: int = 3) -> np.ndarray:
    """Compute and return NDVI array in range [-1.0, 1.0].

    Raises exceptions on invalid input so callers (e.g. analysis) can handle them.
    """
    img = Image.open(input_path)
    arr = np.array(img)
    if arr.ndim == 2:
        raise ValueError("single-band image: cannot compute NDVI")
    if arr.ndim != 3:
        raise ValueError(f"unsupported array shape: {arr.shape}")

    h, w, c = arr.shape
    if red_index < 0 or red_index >= c or nir_index < 0 or nir_index >= c:
        raise ValueError("red_index or nir_index out of range for image channels")

    red = arr[..., red_index].astype(float)
    nir = arr[..., nir_index].astype(float)

    denom = (nir + red)
    denom[denom == 0] = 1e-6
    ndvi = (nir - red) / denom
    ndvi = np.clip(ndvi, -1.0, 1.0)
    return ndvi

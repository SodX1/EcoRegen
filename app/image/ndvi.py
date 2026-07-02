from PIL import Image
import numpy as np
import os
from typing import Optional, Dict, Any


class NDVIResult:
    """Container for NDVI result with helper methods similar to detection results.

    Attributes:
        ndvi: numpy array with values in [-1, 1]
        source: original image path or None
        image: original image array (H,W,3) if available
        meta: optional dict with user-provided metadata
    """

    def __init__(self, ndvi: np.ndarray, source: Optional[str] = None, image: Optional[np.ndarray] = None, meta: Optional[Dict[str, Any]] = None):
        self.ndvi = ndvi
        self.source = source
        self.image = image
        self.meta = meta or {}

    def to_visual(self) -> Image.Image:
        """Convert NDVI array to an RGB PIL image for visualization.

        Positive NDVI -> green, negative -> red, neutral -> yellow.
        """
        ndvi = np.clip(self.ndvi, -1.0, 1.0)
        ndvi_norm = (ndvi + 1.0) / 2.0

        # Continuous red -> yellow -> green gradient.
        # This avoids saturating the green channel for all ndvi > 0 (which hides detail).
        t = ndvi_norm.astype(np.float32)
        r = np.empty_like(t)
        g = np.empty_like(t)

        low = t <= 0.5
        # [-1..0] => red(255,0,0) -> yellow(255,255,0)
        r[low] = 255.0
        g[low] = (t[low] * 2.0) * 255.0

        high = ~low
        # [0..+1] => yellow(255,255,0) -> green(0,255,0)
        r[high] = (1.0 - (t[high] - 0.5) * 2.0) * 255.0
        g[high] = 255.0

        r = np.clip(r, 0.0, 255.0).astype(np.uint8)
        g = np.clip(g, 0.0, 255.0).astype(np.uint8)
        b = np.zeros_like(r, dtype=np.uint8)

        rgb = np.stack([r, g, b], axis=-1)
        return Image.fromarray(rgb)

    def plot(self, show_mask: bool = True, overlay: bool = False, alpha: float = 0.5, save_path: Optional[str] = None, show: bool = True) -> Image.Image:
        """Return (and optionally show/save) a visualization image.

        - show_mask: if True, returns the NDVI visualization alone
        - overlay: if True and original image is available, overlay NDVI colorization on original
        - alpha: transparency for overlay
        - save_path: optional path to save PNG
        - show: if True, call PIL.Image.show() to open the image
        """
        vis = self.to_visual()

        if overlay and self.image is not None:
            base = Image.fromarray(self.image.astype(np.uint8))
            vis = Image.blend(base.convert("RGBA"), vis.convert("RGBA"), alpha=alpha)

        if save_path:
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            vis.save(save_path, format="PNG")

        if show:
            try:
                vis.show()
            except Exception:
                pass

        return vis


def compute_ndvi(input_path: str, red_index: int = 0, nir_index: int = 3, band_names: Optional[list] = None, rgb_indices: Optional[list] = None, rgb_names: Optional[list] = None) -> NDVIResult:
    """Compute NDVI and return NDVIResult.

    - input_path: path to image file
    - red_index, nir_index: integer indices (0-based) for red and NIR channels when using numeric indexing
    - band_names: optional list of band names in order of channels (e.g. ['B02','B03','B04','B08'])

    If `band_names` is provided you can pass indices by looking up names externally; this function accepts indices only.
    """
    img = Image.open(input_path)
    arr = np.array(img)
    image_arr = None
    if arr.ndim == 2:
        raise ValueError("single-band image: cannot compute NDVI")
    if arr.ndim != 3:
        raise ValueError(f"unsupported array shape: {arr.shape}")

    # map rgb_names to indices if possible
    if rgb_indices is None and rgb_names and band_names:
        mapped = []
        for name in rgb_names:
            try:
                mapped.append(band_names.index(name))
            except Exception:
                mapped.append(None)
        if all(m is not None for m in mapped):
            rgb_indices = mapped

    # build an RGB array for optional overlay:
    # prefer explicit rgb_indices if provided, otherwise use first 3 channels when available
    if rgb_indices:
        # ensure provided indices are valid
        try:
            rgb_idx = [int(i) for i in rgb_indices]
        except Exception:
            rgb_idx = []
        if len(rgb_idx) == 3 and max(rgb_idx) < arr.shape[2]:
            image_arr = np.stack([arr[..., rgb_idx[0]], arr[..., rgb_idx[1]], arr[..., rgb_idx[2]]], axis=-1)
    if image_arr is None and arr.shape[2] >= 3:
        image_arr = arr[..., :3]

    # fallback for RGB-only inputs: if nir_index is out of range, use green channel
    if arr.shape[2] >= 2:
        if red_index < 0 or red_index >= arr.shape[2]:
            red_index = 0
        if nir_index < 0 or nir_index >= arr.shape[2]:
            nir_index = 1

    ndvi = compute_ndvi_array_from_array(arr, red_index=red_index, nir_index=nir_index)
    return NDVIResult(ndvi=ndvi, source=input_path, image=image_arr, meta={"red_index": red_index, "nir_index": nir_index, "band_names": band_names})


def compute_ndvi_array_from_array(arr: np.ndarray, red_index: int = 0, nir_index: int = 3) -> np.ndarray:
    """Compute NDVI from a numpy image array and return NDVI in [-1,1]."""
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


def compute_ndvi_array(input_path: str, red_index: int = 0, nir_index: int = 3) -> np.ndarray:
    """Backward-compatible wrapper: compute NDVI array from an image path.

    This restores the original function name used elsewhere in the codebase.
    """
    img = Image.open(input_path)
    arr = np.array(img)
    return compute_ndvi_array_from_array(arr, red_index=red_index, nir_index=nir_index)


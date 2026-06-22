"""Configuration constants for the Clay v1.5 adapter.

All Clay-specific values are isolated here so the rest of the codebase
never hardcodes Clay assumptions (per Roadmap correction #3).
"""

# Model checkpoint location (downloaded from HuggingFace).
CLAY_CHECKPOINT_URL = "https://huggingface.co/made-with-clay/Clay/resolve/main/v1.5/clay-v1.5.ckpt"
CLAY_CHECKPOINT_PATH = "~/.cache/clay/clay-v1.5.ckpt"

# Clay v1.5 large model hyperparameters (from checkpoint).
CLAY_MODEL_SIZE = "large"
CLAY_MASK_RATIO = 0.0  # 0.0 for inference (no masking)
CLAY_PATCH_SIZE = 8
CLAY_NORM_PIX_LOSS = False
CLAY_SHUFFLE = False
CLAY_TEACHER = "vit_large_patch14_reg4_dinov2.lvd142m"
CLAY_DOLLS = [16, 32, 64, 128, 256, 768, 1024]
CLAY_DOLL_WEIGHTS = [1, 1, 1, 1, 1, 1, 1]

# Sentinel-2 L2A band ordering expected by Clay (12 bands).
CLAY_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]

# Wavelengths in nm for Clay's spectral position encoding.
CLAY_WAVELENGTHS = [443, 490, 560, 665, 705, 740, 783, 842, 865, 945, 1610, 2190]

# RGB indices in the 12-band ordering (B04=idx3, B03=idx2, B02=idx1).
CLAY_RGB_INDICES = [3, 2, 1]

# Spatial dimensions.
CLAY_CHIP_SIZE = 256
CLAY_EMBEDDING_DIM = 1024

# GSD (ground sample distance) in meters for Sentinel-2.
CLAY_GSD = 10.0

# Metadata dict for Clay model (Box-structured).
CLAY_METADATA = {
    "sentinel-2-l2a": {
        "bands": {
            "wavelength": dict(zip(CLAY_BANDS, CLAY_WAVELENGTHS, strict=True)),
            "mean": {b: 1000 for b in CLAY_BANDS},
            "std": {b: 2000 for b in CLAY_BANDS},
        },
        "gsd": CLAY_GSD,
        "rgb_indices": CLAY_RGB_INDICES,
    }
}

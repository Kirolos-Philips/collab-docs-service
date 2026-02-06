import io
from datetime import datetime
from pathlib import Path

from PIL import Image

from src.core.config import settings

# Configuration for avatar variants
AVATAR_SIZES = {
    "thumb": (50, 50),
    "medium": (200, 200),
}
# Directory for uploads
UPLOAD_DIR = Path(settings.MEDIA_ROOT) / "images"


async def process_avatar(user_id: str, file_content: bytes) -> dict[str, str]:
    """
    Process an uploaded avatar:
    1. Resize into thumb (50x50) and medium (200x200) variants.
    2. Save as .webp for better performance.
    3. Return public URLs for the variants.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # Relative path for storage and URLs
    rel_path = f"{user_id}/{timestamp}"
    user_upload_dir = UPLOAD_DIR / rel_path
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(io.BytesIO(file_content))

    # Convert to RGB if necessary (e.g. RGBA png)
    if img.mode != "RGB":
        img = img.convert("RGB")

    variants = {}

    # Process variants

    for name, size in AVATAR_SIZES.items():
        filename = f"{name}.webp"
        filepath = user_upload_dir / filename

        # Using thumbnail which maintains aspect ratio but scales down
        variant_img = img.copy()

        # We want square avatars, so we crop first then resize
        w, h = variant_img.size
        min_dim = min(w, h)
        left = (w - min_dim) / 2
        top = (h - min_dim) / 2
        right = (w + min_dim) / 2
        bottom = (h + min_dim) / 2

        variant_img = variant_img.crop((left, top, right, bottom))
        variant_img = variant_img.resize(size, Image.LANCZOS)
        variant_img.save(filepath, "WEBP", quality=85)

        # Public URL
        variants[name] = f"/{filepath}"

    # Also save original as webp
    original_filename = "original.webp"
    original_path = user_upload_dir / original_filename
    img.save(original_path, "WEBP", quality=90)
    variants["original"] = f"/{original_path}"
    return variants

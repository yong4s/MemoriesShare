import logging
import os
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)

IMAGE_MIME_TYPES = frozenset({
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/webp',
})


def is_image_mime_type(mime_type: str) -> bool:
    """Check if MIME type is a supported image format."""
    return mime_type.lower() in IMAGE_MIME_TYPES


def derive_thumbnail_key(original_s3_key: str) -> str:
    """Derive thumbnail S3 key from original key.

    Replaces '/originals/' with '/processed/thumbnails/' and changes extension to .jpg.

    Example:
        'users/.../albums/.../originals/abc.png'
        → 'users/.../albums/.../processed/thumbnails/abc.jpg'
    """
    thumbnail_key = original_s3_key.replace('/originals/', '/processed/thumbnails/')
    base, _ = os.path.splitext(thumbnail_key)
    return f'{base}.jpg'


def generate_thumbnail_bytes(
    image_bytes: bytes,
    max_width: int = 400,
    quality: int = 80,
) -> bytes:
    """Resize image and return JPEG thumbnail bytes.

    Maintains aspect ratio. Converts RGBA/P to RGB for JPEG compatibility.
    For animated GIFs, only the first frame is used.
    """
    img = Image.open(BytesIO(image_bytes))

    # Handle animated images — take first frame
    if hasattr(img, 'n_frames') and img.n_frames > 1:
        img.seek(0)

    # Convert palette and RGBA modes to RGB
    if img.mode in ('RGBA', 'P', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize maintaining aspect ratio
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    output = BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    return output.getvalue()

"""
Input validation utilities for uploaded images and geographic coordinates.
"""

from pathlib import Path
from typing import Tuple

from PIL import Image, UnidentifiedImageError
import io

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "application/octet-stream"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_IMAGE_DIMENSION = 64


class ValidationError(Exception):
    """Raised when user-supplied input fails validation."""


def validate_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """Ensure latitude is within [-90, 90] and longitude is within [-180, 180]."""
    if latitude is None or longitude is None:
        raise ValidationError("Both latitude and longitude are required.")
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Latitude and longitude must be numbers.") from exc

    if not (-90.0 <= lat <= 90.0):
        raise ValidationError("Latitude must be between -90 and 90 degrees.")
    if not (-180.0 <= lon <= 180.0):
        raise ValidationError("Longitude must be between -180 and 180 degrees.")
    return lat, lon


def validate_image_upload(filename: str, content_type: str | None, data: bytes) -> dict:
    """Validate uploaded image file extension, size, and integrity."""
    if not filename:
        raise ValidationError("Uploaded file has no filename.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '{ext or 'unknown'}'. Please upload a JPG, JPEG, or PNG image."
        )

    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported content type '{content_type}'. Please upload a JPG or PNG photograph."
        )

    if not data:
        raise ValidationError("The uploaded file is empty.")

    if len(data) > MAX_IMAGE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        raise ValidationError(
            f"Image is too large ({size_mb:.1f} MB). Maximum allowed size is 10 MB."
        )

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            fmt = (img.format or "").upper()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValidationError(
            "The uploaded file is not a valid image or appears to be corrupted."
        ) from exc

    if fmt not in {"JPEG", "PNG", "MPO"}:
        raise ValidationError(
            f"Unsupported image encoding '{fmt}'. Please upload a standard JPG or PNG image."
        )

    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise ValidationError(
            f"Image resolution ({width}x{height}) is too small. Please upload a clearer leaf photo (at least {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION} px)."
        )

    return {
        "filename": Path(filename).name,
        "size_bytes": len(data),
        "width": width,
        "height": height,
        "format": fmt,
    }

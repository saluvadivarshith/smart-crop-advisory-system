"""
Image preprocessing shared by training and inference.

* Training images get random augmentation (crop, flip, rotation, colour
  changes) so the model copes with different phones, angles and lighting.
* Inference images get the same deterministic resize + normalisation used
  for validation.
* ``image_quality`` gives simple brightness / sharpness checks so that the
  farmer can be asked to retake a dark or blurry photo.
"""

import io

import numpy as np
from PIL import Image, ImageOps

IMG_SIZE = 224
# ImageNet statistics – required because we start from ImageNet weights.
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

# Heuristic quality thresholds (on a 512 px grayscale copy).
DARK_THRESHOLD = 40
BRIGHT_THRESHOLD = 225
BLUR_THRESHOLD = 40.0


def train_transforms(img_size=IMG_SIZE):
    from torchvision import transforms
    return transforms.Compose([
        transforms.RandomResizedCrop(img_size, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.03),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def eval_transforms(img_size=IMG_SIZE):
    from torchvision import transforms
    return transforms.Compose([
        transforms.Resize(int(img_size * 256 / 224)),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def load_image(data: bytes) -> Image.Image:
    """Open image bytes, apply the phone's EXIF rotation and convert to RGB."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def image_quality(img: Image.Image) -> dict:
    gray = img.convert("L")
    gray.thumbnail((512, 512))
    a = np.asarray(gray, dtype=np.float32)
    brightness = float(a.mean())
    # Variance of the Laplacian: low values mean few sharp edges (blurry).
    lap = a[1:-1, :-2] + a[1:-1, 2:] + a[:-2, 1:-1] + a[2:, 1:-1] - 4 * a[1:-1, 1:-1]
    sharpness = float(lap.var())

    warnings = []
    if brightness < DARK_THRESHOLD:
        warnings.append("The photo is too dark. Take it in daylight.")
    elif brightness > BRIGHT_THRESHOLD:
        warnings.append("The photo is too bright or washed out. Avoid direct glare.")
    if sharpness < BLUR_THRESHOLD:
        warnings.append("The photo looks blurry. Hold the phone steady and focus on the leaf.")

    return {
        "brightness": round(brightness, 1),
        "sharpness": round(sharpness, 1),
        "ok": not warnings,
        "warnings": warnings,
    }

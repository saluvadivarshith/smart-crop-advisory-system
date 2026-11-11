"""
Dataset discovery and train / validation / test splitting.

Supported layouts (``--data-dir`` points at the folder you extracted):

1. Class folders directly (e.g. Kaggle "emmarex/plantdisease"):
       PlantVillage/Tomato_Early_blight/*.jpg ...
2. PlantVillage "color / grayscale / segmented" (Kaggle
   "abdallahalidev/plantvillage-dataset") – the "color" folder is used.
3. Pre-split "train / valid" (Kaggle "vipoooool/new-plant-diseases-dataset")
   – "valid" becomes the held-out TEST set and a validation set is carved out
   of "train".

Splits are stratified per class with a fixed random seed so results are
reproducible, and the test set is never used for training or model selection.
"""

import os
import random
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def _has_any_image(folder: Path) -> bool:
    """Fast O(1) check whether a directory contains at least one image file."""
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in IMAGE_EXTS:
                    return True
    except OSError:
        pass
    return False


def _images_in(folder: Path) -> list[Path]:
    """Fast directory listing using os.scandir."""
    paths = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in IMAGE_EXTS:
                    paths.append(Path(entry.path))
    except OSError:
        return []
    paths.sort()
    return paths


def _is_class_root(folder: Path) -> bool:
    subdirs = [d for d in folder.iterdir() if d.is_dir()]
    if len(subdirs) < 2:
        return False
    count = 0
    for d in subdirs:
        if _has_any_image(d):
            count += 1
            if count >= 2:
                return True
    return False


def find_class_root(folder: Path) -> Path:
    """Walk down wrapper folders (preferring 'color') until we reach class folders."""
    folder = Path(folder)
    for _ in range(5):
        subdirs = {d.name.lower(): d for d in folder.iterdir() if d.is_dir()}
        if "color" in subdirs:
            folder = subdirs["color"]
            continue
        if _is_class_root(folder):
            return folder
        if len(subdirs) == 1:
            folder = next(iter(subdirs.values()))
        else:
            break
    if _is_class_root(folder):
        return folder
    raise FileNotFoundError(f"Could not find class folders with images under '{folder}'.")


def _find_presplit(root: Path):
    for _ in range(4):
        subdirs = {d.name.lower(): d for d in root.iterdir() if d.is_dir()}
        test_dir = subdirs.get("valid") or subdirs.get("val") or subdirs.get("test")
        if "train" in subdirs and test_dir:
            return find_class_root(subdirs["train"]), find_class_root(test_dir)
        if len(subdirs) == 1:
            root = next(iter(subdirs.values()))
        else:
            return None
    return None


def _collect(class_root: Path, class_names):
    per_class = {}
    for name in class_names:
        folder = class_root / name
        per_class[name] = _images_in(folder) if folder.is_dir() else []
    return per_class


def build_splits(data_dir, crops=None, val_split=0.15, test_split=0.15, max_per_class=None, seed=42):
    """Return (class_names, train, val, test) where each split is [(path, label)]."""
    from backend.ml.labels import parse_class_name

    data_dir = Path(data_dir)
    rng = random.Random(seed)
    presplit = _find_presplit(data_dir)
    train_root = presplit[0] if presplit else find_class_root(data_dir)

    wanted = {c.lower() for c in crops} if crops else None
    candidate_dirs = sorted(d.name for d in train_root.iterdir() if d.is_dir())
    if wanted:
        candidate_dirs = [
            c for c in candidate_dirs if parse_class_name(c)["crop_key"] in wanted
        ]
    class_names = [c for c in candidate_dirs if _has_any_image(train_root / c)]
    if not class_names:
        raise ValueError(f"No classes with images found for crops {crops} in {train_root}.")

    label_of = {name: i for i, name in enumerate(class_names)}

    train, val, test = [], [], []
    train_images = _collect(train_root, class_names)
    test_images = _collect(presplit[1], class_names) if presplit else None

    for name in class_names:
        imgs = list(train_images[name])
        rng.shuffle(imgs)
        if max_per_class:
            imgs = imgs[:max_per_class]
        label = label_of[name]
        if presplit:
            n_val = max(1, int(len(imgs) * val_split))
            val += [(p, label) for p in imgs[:n_val]]
            train += [(p, label) for p in imgs[n_val:]]
            t_imgs = list(test_images[name])
            rng.shuffle(t_imgs)
            if max_per_class:
                t_imgs = t_imgs[:max(1, int(max_per_class * test_split))]
            test += [(p, label) for p in t_imgs]
        else:
            n_test = max(1, int(len(imgs) * test_split))
            n_val = max(1, int(len(imgs) * val_split))
            test += [(p, label) for p in imgs[:n_test]]
            val += [(p, label) for p in imgs[n_test:n_test + n_val]]
            train += [(p, label) for p in imgs[n_test + n_val:]]

    rng.shuffle(train)
    return class_names, train, val, test


class ImageListDataset:
    """Minimal torch Dataset over a list of (path, label) pairs."""

    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        from PIL import Image
        path, label = self.samples[idx]
        with Image.open(path) as img:
            img = img.convert("RGB")
        return self.transform(img), label

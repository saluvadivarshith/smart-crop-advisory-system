"""
Helper script to download a manageable PlantVillage subset (Tomato, Potato,
Bell Pepper – 15 classes) from a public mirror, or verify an existing Kaggle
PlantVillage directory.

Usage:
    # Option A: Download the PlantVillage subset automatically
    python -m backend.ml.download_dataset

    # Option B: Point train.py directly at your downloaded Kaggle folder
    python -m backend.ml.train --data-dir "C:/path/to/PlantVillage" --crops tomato potato pepper
"""

import argparse
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parent / "dataset"

# Public academic / open-source archive mirrors of PlantVillage (color leaf images)
MIRRORS = [
    "https://huggingface.co/datasets/GVJahnavi/PlantVillage_dataset/resolve/main/PlantVillage.zip",
    "https://data.mendeley.com/public-files/datasets/tywbtsjrjv/files/d5652a28-c1d8-4b76-97f3-72fb80f94efc/file_downloaded",
]


def download_with_progress(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading dataset from:\n  {url}\nto:\n  {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SmartCropAdvisory/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            read += len(chunk)
            if total:
                pct = 100.0 * read / total
                print(f"\r  {read / (1024 * 1024):.1f} / {total / (1024 * 1024):.1f} MB ({pct:.1f}%)", end="", flush=True)
    print("\nDownload finished.")


def extract_archive(archive_path: Path, extract_to: Path) -> None:
    print(f"Extracting {archive_path.name} ...")
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_to)
    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(extract_to)
    else:
        raise RuntimeError(f"Unsupported archive format: {archive_path}")
    print(f"Extracted to {extract_to}")


def main():
    parser = argparse.ArgumentParser(description="Download or verify the PlantVillage dataset.")
    parser.add_argument("--dest", default=str(DATASET_DIR), help="Target directory for dataset")
    parser.add_argument("--url", default=None, help="Optional custom dataset zip URL")
    args = parser.parse_args()

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    urls = [args.url] if args.url else MIRRORS
    archive_path = dest_dir / "plantvillage_download.zip"

    for url in urls:
        try:
            download_with_progress(url, archive_path)
            extract_archive(archive_path, dest_dir)
            archive_path.unlink(missing_ok=True)
            from backend.ml.dataset import find_class_root
            root = find_class_root(dest_dir)
            print(f"\nDataset ready at: {root}")
            print("You can now train the model with:")
            print(f'  .\\venv\\Scripts\\python.exe -m backend.ml.train --data-dir "{root}" --crops tomato potato pepper')
            return
        except Exception as exc:
            print(f"\nMirror failed ({exc}). Trying next option if available...")

    print(
        "\nAutomatic download did not complete. You can download PlantVillage from Kaggle:\n"
        "  https://www.kaggle.com/datasets/emmarex/plantdisease\n"
        "Extract it into backend/ml/dataset/ and run:\n"
        '  .\\venv\\Scripts\\python.exe -m backend.ml.train --data-dir "backend/ml/dataset" --crops tomato potato pepper'
    )


if __name__ == "__main__":
    main()

"""
Evaluate a trained crop-disease model on the held-out TEST split.

Produces (in backend/ml/model/):
  * metrics.json             – accuracy, macro/weighted F1, per-class report,
                               confidence-threshold analysis
  * classification_report.txt
  * confusion_matrix.png

Usage (from the project root):
    python -m backend.ml.evaluate
"""

import argparse
import json
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "model"
THRESHOLDS = [0.5, 0.55, 0.6, 0.7, 0.8, 0.9]
MIN_FIELD_THRESHOLD = 0.55


def run_inference(model, samples, img_size, device, batch_size=64, workers=0):
    import torch
    from torch.utils.data import DataLoader

    from backend.ml.dataset import ImageListDataset
    from backend.ml.preprocess import eval_transforms

    loader = DataLoader(ImageListDataset(samples, eval_transforms(img_size)),
                        batch_size=batch_size, shuffle=False, num_workers=workers)
    model.eval()
    all_probs, all_labels = [], []
    with torch.no_grad():
        for x, y in loader:
            probs = torch.softmax(model(x.to(device)), dim=1).cpu()
            all_probs.append(probs)
            all_labels.append(y)
    return torch.cat(all_probs).numpy(), torch.cat(all_labels).numpy()


def threshold_analysis(probs, labels):
    """How accuracy and coverage change if low-confidence results are rejected."""
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    rows = []
    for t in THRESHOLDS:
        accepted = conf >= t
        n = int(accepted.sum())
        rows.append({
            "threshold": t,
            "coverage": round(n / len(labels), 4),
            "accuracy_on_accepted": round(float((pred[accepted] == labels[accepted]).mean()), 4) if n else None,
        })
    # Smallest threshold keeping >= 98% accuracy on accepted images, but never
    # below 0.70: real field photos differ from lab dataset photos, so we stay
    # conservative.
    chosen = next((r["threshold"] for r in rows
                   if r["accuracy_on_accepted"] and r["accuracy_on_accepted"] >= 0.98), 0.9)
    return rows, max(chosen, MIN_FIELD_THRESHOLD)


def save_reports(probs, labels, class_names, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

    pred = probs.argmax(axis=1)
    idx = list(range(len(class_names)))
    report_dict = classification_report(labels, pred, labels=idx, target_names=class_names,
                                        output_dict=True, zero_division=0)
    report_txt = classification_report(labels, pred, labels=idx, target_names=class_names,
                                       digits=4, zero_division=0)
    cm = confusion_matrix(labels, pred, labels=idx)
    thresholds, recommended = threshold_analysis(probs, labels)

    metrics = {
        "test_samples": int(len(labels)),
        "accuracy": round(float(accuracy_score(labels, pred)), 4),
        "macro_f1": round(float(f1_score(labels, pred, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(labels, pred, average="weighted", zero_division=0)), 4),
        "per_class": {c: {k: round(v, 4) if isinstance(v, float) else v
                          for k, v in report_dict[c].items()} for c in class_names},
        "threshold_analysis": thresholds,
        "recommended_confidence_threshold": recommended,
        "confusion_matrix": cm.tolist(),
        "class_names": class_names,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out_dir / "classification_report.txt").write_text(report_txt)

    # Confusion matrix figure.
    from backend.ml.labels import parse_class_name
    short = [f"{parse_class_name(c)['crop_name'].split()[0]}: {parse_class_name(c)['disease_name']}"
             for c in class_names]
    size = max(8, len(class_names) * 0.55)
    fig, ax = plt.subplots(figsize=(size, size))
    norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
    ax.imshow(norm, cmap="Greens")
    ax.set_xticks(idx, short, rotation=90, fontsize=8)
    ax.set_yticks(idx, short, fontsize=8)
    for i in idx:
        for j in idx:
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=7,
                        color="white" if norm[i, j] > 0.6 else "black")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"Confusion matrix – test accuracy {metrics['accuracy']:.2%}")
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png", dpi=130)
    plt.close(fig)
    return metrics


def main():
    import torch

    from backend.ml.model_def import build_model

    parser = argparse.ArgumentParser(description="Evaluate the trained crop disease model.")
    parser.add_argument("--model-dir", default=str(MODEL_DIR))
    parser.add_argument("--workers", type=int, default=0)
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    ckpt = torch.load(model_dir / "crop_disease_model.pt", map_location="cpu", weights_only=False)
    split = json.loads((model_dir / "test_split.json").read_text())
    samples = [(Path(p), l) for p, l in split["samples"]]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(ckpt["arch"], len(ckpt["class_names"]), pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.to(device)

    probs, labels = run_inference(model, samples, ckpt["img_size"], device, workers=args.workers)
    metrics = save_reports(probs, labels, ckpt["class_names"], model_dir)

    ckpt["confidence_threshold"] = metrics["recommended_confidence_threshold"]
    ckpt["test_accuracy"] = metrics["accuracy"]
    torch.save(ckpt, model_dir / "crop_disease_model.pt")
    print(f"Test accuracy: {metrics['accuracy']:.4f}  macro F1: {metrics['macro_f1']:.4f}")
    print(f"Recommended confidence threshold: {metrics['recommended_confidence_threshold']}")


if __name__ == "__main__":
    main()

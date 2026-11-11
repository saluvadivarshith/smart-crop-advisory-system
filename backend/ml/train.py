"""
Train a lightweight crop-disease classifier with transfer learning.

Phase 1: freeze the ImageNet-pretrained backbone and train only the new
         classification layer (fast, stable).
Phase 2: unfreeze everything and fine-tune with a smaller learning rate.

The best epoch is chosen on the VALIDATION split. The TEST split is used once
at the end (see evaluate.py) so the reported accuracy is honest.

Example (from the project root, with the venv active):
    python -m backend.ml.train --data-dir "D:/datasets/PlantVillage" --crops tomato potato pepper
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "model"


def parse_args():
    from backend.ml.model_def import SUPPORTED_ARCHS
    p = argparse.ArgumentParser(description="Train the crop disease classifier.")
    p.add_argument("--data-dir", default="plantvillage dataset", help="Folder containing the extracted dataset")
    p.add_argument("--output-dir", default=str(MODEL_DIR))
    p.add_argument("--arch", default="mobilenet_v3_large", choices=SUPPORTED_ARCHS)
    p.add_argument("--crops", nargs="*", default=None,
                   help="Only use these crops, e.g. --crops tomato potato pepper")
    p.add_argument("--epochs", type=int, default=8, help="Fine-tuning epochs (phase 2)")
    p.add_argument("--freeze-epochs", type=int, default=2, help="Head-only epochs (phase 1)")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--img-size", type=int, default=224)
    p.add_argument("--val-split", type=float, default=0.15)
    p.add_argument("--test-split", type=float, default=0.15)
    p.add_argument("--max-per-class", type=int, default=None,
                   help="Cap images per class (faster experiments)")
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None):
    import torch
    training = optimizer is not None
    model.train(training)
    total, correct, loss_sum = 0, 0, 0.0
    use_amp = device == "cuda"
    with torch.set_grad_enabled(training):
        for x, y in loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", enabled=use_amp):
                out = model(x)
                loss = criterion(out, y)
            if training:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            loss_sum += loss.item() * y.size(0)
            correct += (out.argmax(1) == y).sum().item()
            total += y.size(0)
    return loss_sum / total, correct / total


def save_history_plot(history, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    epochs = [h["epoch"] for h in history]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.plot(epochs, [h["train_loss"] for h in history], label="train")
    a1.plot(epochs, [h["val_loss"] for h in history], label="validation")
    a1.set_title("Loss"); a1.set_xlabel("epoch"); a1.legend()
    a2.plot(epochs, [h["train_acc"] for h in history], label="train")
    a2.plot(epochs, [h["val_acc"] for h in history], label="validation")
    a2.set_title("Accuracy"); a2.set_xlabel("epoch"); a2.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "training_curves.png", dpi=120)
    plt.close(fig)


def main():
    args = parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    from backend.ml.dataset import ImageListDataset, build_splits
    from backend.ml.evaluate import run_inference, save_reports
    from backend.ml.labels import parse_class_name
    from backend.ml.model_def import backbone_parameters, build_model
    from backend.ml.preprocess import MEAN, STD, eval_transforms, train_transforms

    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    class_names, train, val, test = build_splits(
        args.data_dir, args.crops, args.val_split, args.test_split, args.max_per_class, args.seed)
    print(f"Device: {device} | classes: {len(class_names)} | "
          f"train {len(train)} / val {len(val)} / test {len(test)}")
    for c in class_names:
        info = parse_class_name(c)
        print(f"  {c:55s} -> {info['crop_name']} / {info['disease_name']}")

    # Save the test split so evaluate.py can reproduce results exactly.
    (out_dir / "test_split.json").write_text(json.dumps(
        {"class_names": class_names, "samples": [(str(p), l) for p, l in test]}))

    loader_kwargs = dict(batch_size=args.batch_size, num_workers=args.workers,
                         pin_memory=device == "cuda", persistent_workers=args.workers > 0)
    train_loader = DataLoader(ImageListDataset(train, train_transforms(args.img_size)), shuffle=True, **loader_kwargs)
    val_loader = DataLoader(ImageListDataset(val, eval_transforms(args.img_size)), shuffle=False, **loader_kwargs)

    model = build_model(args.arch, len(class_names), pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")

    history, best_acc, best_state = [], 0.0, None
    total_epochs = args.freeze_epochs + args.epochs
    start = time.time()

    for epoch in range(1, total_epochs + 1):
        if epoch == 1:
            for p in backbone_parameters(model):
                p.requires_grad = False
            optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)
            scheduler = None
            print("Phase 1: training classifier head (backbone frozen)")
        if epoch == args.freeze_epochs + 1:
            for p in model.parameters():
                p.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr * 0.1, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))
            print("Phase 2: fine-tuning the whole network")

        tl, ta = run_epoch(model, train_loader, criterion, device, optimizer, scaler)
        vl, va = run_epoch(model, val_loader, criterion, device)
        if scheduler:
            scheduler.step()
        history.append({"epoch": epoch, "train_loss": round(tl, 4), "train_acc": round(ta, 4),
                        "val_loss": round(vl, 4), "val_acc": round(va, 4)})
        flag = ""
        if va > best_acc:
            best_acc, flag = va, "  <- best"
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        print(f"Epoch {epoch:2d}/{total_epochs}  train loss {tl:.4f} acc {ta:.4f} | "
              f"val loss {vl:.4f} acc {va:.4f}{flag}")

    minutes = (time.time() - start) / 60
    model.load_state_dict(best_state)

    print("Evaluating best model on the held-out test split ...")
    probs, labels = run_inference(model, test, args.img_size, device, workers=0)
    metrics = save_reports(probs, labels, class_names, out_dir)

    checkpoint = {
        "state_dict": best_state,
        "arch": args.arch,
        "class_names": class_names,
        "classes": [parse_class_name(c) for c in class_names],
        "img_size": args.img_size,
        "mean": MEAN, "std": STD,
        "best_val_accuracy": round(best_acc, 4),
        "test_accuracy": metrics["accuracy"],
        "confidence_threshold": metrics["recommended_confidence_threshold"],
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": Path(args.data_dir).name,
        "split_sizes": {"train": len(train), "val": len(val), "test": len(test)},
        "training_minutes": round(minutes, 1),
    }
    torch.save(checkpoint, out_dir / "crop_disease_model.pt")
    (out_dir / "training_history.json").write_text(json.dumps(history, indent=2))
    save_history_plot(history, out_dir)

    print(f"\nSaved model to {out_dir / 'crop_disease_model.pt'}")
    print(f"Best validation accuracy: {best_acc:.4f}")
    print(f"Test accuracy: {metrics['accuracy']:.4f} | macro F1: {metrics['macro_f1']:.4f}")
    print(f"Confidence threshold for 'uncertain': {metrics['recommended_confidence_threshold']}")
    print(f"Training time: {minutes:.1f} min")


if __name__ == "__main__":
    main()

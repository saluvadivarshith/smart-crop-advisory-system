"""
Inference, Multi-View Test-Time Augmentation (TTA), Vegetable/Leaf Symptom
Calibration, and Grad-CAM explainability wrapper around the trained PyTorch model.

Why this hybrid multi-view pipeline matters:
1. The 38-class MobileNetV3-Large model is trained on PlantVillage leaf images
   (which have neutral mid-gray studio backgrounds and flat leaves).
2. When a farmer uploads a real-world field photo (with white, dark, soil, or sky
   backgrounds) OR a vegetable/fruit/tuber photo (tomato fruit, potato tuber,
   bell pepper pod, apple, citrus, etc.), a single raw center-crop pass can lose
   lesions near edges or suffer from background/domain shift.
3. ``predict_with_gradcam`` therefore combines:
   - 4-view TTA (full frame, center crop, studio-gray background-normalized ROI,
     and zoomed lesion patch),
   - Organ & surface lesion profiling (detecting whether the sample is a leaf or
     a vegetable/fruit/tuber and quantifying necrotic, spotted, chlorotic, rust,
     powdery, or healthy surface features),
   - Crop-aware logit calibration, and
   - Resolution-enhanced Grad-CAM + lesion attention heatmaps.
"""

import base64
import io
import threading
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

MODEL_PATH = Path(__file__).resolve().parent / "model" / "crop_disease_model.pt"


def _apply_jet_colormap(norm_cam: np.ndarray) -> np.ndarray:
    """Map a normalized [0, 1] 2D array to an RGB thermal colormap [H, W, 3] uint8."""
    v = np.clip(norm_cam, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * v - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * v - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * v - 1.0), 0.0, 1.0)
    rgb = np.stack([r, g, b], axis=-1)
    return (rgb * 255).astype(np.uint8)


def _pil_to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def analyze_foreground_and_symptoms(img: Image.Image) -> dict:
    """
    Segment the foreground plant/vegetable from uniform backgrounds (white, black,
    gray studio, or sky) and compute surface symptom indicators.
    """
    work = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
    arr = np.asarray(work, dtype=np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c
    sat = np.where(max_c > 1e-4, delta / (max_c + 1e-4), 0.0)
    val = max_c

    # Estimate background color from outer border pixels (4px frame)
    border_pixels = np.concatenate([
        arr[:6, :, :].reshape(-1, 3),
        arr[-6:, :, :].reshape(-1, 3),
        arr[:, :6, :].reshape(-1, 3),
        arr[:, -6:, :].reshape(-1, 3),
    ], axis=0)
    bg_median = np.median(border_pixels, axis=0)
    bg_dist = np.linalg.norm(arr - bg_median[None, None, :], axis=-1)

    # A pixel is foreground if it differs from the border background OR has strong plant/produce color
    is_white_bg = (r > 0.88) & (g > 0.88) & (b > 0.88) & (sat < 0.14)
    is_black_bg = val < 0.08
    has_plant_color = (sat > 0.15) & (~is_white_bg) & (~is_black_bg)
    fg_mask = ((bg_dist > 0.14) | has_plant_color) & (~is_white_bg) & (~is_black_bg)

    # If the sample fills the entire frame (e.g. close-up of a vegetable or leaf), use inner 85% region
    if fg_mask.mean() < 0.12:
        fg_mask = (~is_white_bg) & (~is_black_bg)
    if fg_mask.mean() < 0.10:
        fg_mask = np.ones((224, 224), dtype=bool)

    # Classify foreground pixels into organ & symptom categories
    green_foliage = fg_mask & (g >= r * 0.88) & (g >= b * 1.04) & (val > 0.15)
    red_orange_produce = fg_mask & (r > g * 1.18) & (r > b * 1.25) & (r > 0.28) & (sat > 0.22)
    tan_tuber_or_stem = fg_mask & (r > b * 1.15) & (g > b * 1.05) & (r >= g * 0.92) & (val > 0.22) & (sat > 0.12) & (~green_foliage)

    fg_count = max(int(fg_mask.sum()), 1)
    green_ratio = float(green_foliage.sum()) / fg_count
    produce_ratio = float((red_orange_produce | tan_tuber_or_stem).sum()) / fg_count

    organ_type = "leaf" if green_ratio >= 0.32 else ("vegetable_or_fruit" if produce_ratio >= 0.18 else "plant_sample")

    # Local contrast / texture for lesion detection (necrotic dark spots, blight, scab, rot)
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    pad = np.pad(gray, 2, mode="edge")
    local_mean = (
        pad[:-4, :-4] + pad[:-4, 2:-2] + pad[:-4, 4:] +
        pad[2:-2, :-4] + pad[2:-2, 2:-2] + pad[2:-2, 4:] +
        pad[4:, :-4] + pad[4:, 2:-2] + pad[4:, 4:]
    ) / 9.0
    local_drop = np.clip(local_mean - gray, 0.0, 1.0)
    local_diff = np.abs(gray - local_mean)

    # 1. Dark necrotic / blight / rot lesions (dark brown, black, or sunken dark patches inside foreground)
    necrotic_mask = fg_mask & (
        ((val < 0.36) & (val > 0.05) & (local_drop > 0.03))
        | ((r > g * 1.08) & (g > b * 1.05) & (val < 0.48) & (local_drop > 0.045))
        | (local_drop > 0.085)
    )
    # 2. Chlorotic / yellow / mosaic / curl patches
    yellow_chlorotic_mask = fg_mask & (r > 0.42) & (g > 0.40) & (b < 0.32) & (np.abs(r - g) < 0.16) & (sat > 0.25)
    # 3. Rust / orange-brown pustules
    rust_mask = fg_mask & (r > 0.38) & (g > 0.18) & (g < 0.48) & (b < 0.22) & (r > g * 1.22) & (local_diff > 0.03)
    # 4. Powdery white/grayish mildew patches on tissue
    powdery_mask = fg_mask & (val > 0.62) & (sat < 0.20) & (local_diff > 0.025) & (~is_white_bg)

    necrotic_ratio = float(necrotic_mask.sum()) / fg_count
    yellow_ratio = float(yellow_chlorotic_mask.sum()) / fg_count
    rust_ratio = float(rust_mask.sum()) / fg_count
    powdery_ratio = float(powdery_mask.sum()) / fg_count
    texture_roughness = float(local_diff[fg_mask].mean()) if fg_mask.any() else 0.0

    # Combined 2D symptom saliency map [224, 224] in [0, 1]
    lesion_map = (
        1.0 * necrotic_mask.astype(np.float32)
        + 0.75 * rust_mask.astype(np.float32)
        + 0.65 * yellow_chlorotic_mask.astype(np.float32)
        + 0.60 * powdery_mask.astype(np.float32)
        + 3.5 * (local_drop * fg_mask.astype(np.float32))
    )
    if lesion_map.max() > 1e-4:
        lesion_map = np.clip(lesion_map / np.percentile(lesion_map[fg_mask], 98.5).clip(min=0.15), 0.0, 1.0)

    # Create studio-gray normalized image (replacing non-foreground background with PlantVillage neutral gray)
    studio_arr = arr.copy()
    studio_gray = np.array([0.49, 0.48, 0.50], dtype=np.float32)
    studio_arr[~fg_mask] = studio_gray
    studio_img = Image.fromarray((np.clip(studio_arr, 0.0, 1.0) * 255).astype(np.uint8))

    # Extract tight foreground ROI crop
    ys, xs = np.where(fg_mask)
    if len(ys) > 20 and len(xs) > 20:
        y0, y1 = max(0, int(ys.min()) - 8), min(224, int(ys.max()) + 8)
        x0, x1 = max(0, int(xs.min()) - 8), min(224, int(xs.max()) + 8)
        if (y1 - y0) >= 48 and (x1 - x0) >= 48:
            roi_img = studio_img.crop((x0, y0, x1, y1)).resize((224, 224), Image.Resampling.BILINEAR)
        else:
            roi_img = studio_img
    else:
        roi_img = studio_img

    # Find highest-lesion sub-window (112x112) to feed a zoomed lesion view
    best_score = -1.0
    best_box = (56, 56, 168, 168)
    for cy in (32, 56, 80, 104):
        for cx in (32, 56, 80, 104):
            patch_score = float(lesion_map[cy:cy + 112, cx:cx + 112].mean())
            if patch_score > best_score:
                best_score = patch_score
                best_box = (cx, cy, cx + 112, cy + 112)
    lesion_patch_img = work.crop(best_box).resize((224, 224), Image.Resampling.BILINEAR)

    symptom_severity = max(
        necrotic_ratio * 3.2,
        rust_ratio * 3.0,
        yellow_ratio * 2.2,
        powdery_ratio * 2.4,
        (texture_roughness - 0.028) * 10.0,
    )
    symptom_severity = float(np.clip(symptom_severity, 0.0, 1.0))

    return {
        "organ_type": organ_type,
        "foreground_ratio": round(float(fg_mask.mean()), 3),
        "green_ratio": round(green_ratio, 3),
        "produce_ratio": round(produce_ratio, 3),
        "necrotic_ratio": round(necrotic_ratio, 4),
        "yellow_ratio": round(yellow_ratio, 4),
        "rust_ratio": round(rust_ratio, 4),
        "powdery_ratio": round(powdery_ratio, 4),
        "texture_roughness": round(texture_roughness, 4),
        "symptom_severity": round(symptom_severity, 3),
        "studio_img": studio_img,
        "roi_img": roi_img,
        "lesion_patch_img": lesion_patch_img,
        "lesion_map_224": lesion_map,
    }


class CropDiseasePredictor:
    def __init__(self, model_path=MODEL_PATH):
        self.model_path = Path(model_path)
        self._lock = threading.Lock()
        self._model = None
        self._meta = None
        self._transform = None
        self._full_transform = None
        self._device = "cpu"
        self._mtime = None

    def is_available(self) -> bool:
        return self.model_path.exists()

    def _load(self):
        if not self.is_available():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        current_mtime = self.model_path.stat().st_mtime
        if self._model is not None and self._mtime == current_mtime:
            return
        with self._lock:
            current_mtime = self.model_path.stat().st_mtime
            if self._model is not None and self._mtime == current_mtime:
                return
            import torch
            from torchvision import transforms
            from backend.ml.model_def import build_model
            from backend.ml.preprocess import MEAN, STD, eval_transforms

            ckpt = torch.load(self.model_path, map_location="cpu", weights_only=False)
            model = build_model(ckpt["arch"], len(ckpt["class_names"]), pretrained=False)
            model.load_state_dict(ckpt["state_dict"])
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(self._device).eval()
            img_sz = ckpt.get("img_size", 224)
            self._transform = eval_transforms(img_sz)
            self._full_transform = transforms.Compose([
                transforms.Resize((img_sz, img_sz)),
                transforms.ToTensor(),
                transforms.Normalize(MEAN, STD),
            ])
            self._meta = {k: v for k, v in ckpt.items() if k != "state_dict"}
            self._model = model
            self._mtime = current_mtime

    @property
    def metadata(self) -> dict:
        self._load()
        return self._meta

    def _compute_calibrated_probs(
        self,
        raw_logits: "torch.Tensor",
        fg_info: dict,
        selected_crop_key: Optional[str] = None,
    ) -> "torch.Tensor":
        """
        Combine 4-view CNN logits with organ/symptom priors and optional crop
        conditioning so both studio leaf samples and real-world vegetable/field
        samples receive well-calibrated probabilities.
        """
        import torch
        from backend.ml.labels import parse_class_name

        classes_meta = self._meta.get("classes") or [
            parse_class_name(c) for c in self._meta["class_names"]
        ]
        num_classes = len(classes_meta)

        # Base temperature-scaled probability from the 4 CNN views
        # raw_logits shape: [4, num_classes] (0: full, 1: center-crop, 2: studio ROI, 3: lesion patch)
        weights_view = torch.tensor([0.32, 0.28, 0.25, 0.15], device=raw_logits.device).unsqueeze(1)
        combined_logits = (raw_logits * weights_view).sum(dim=0)

        # Check how confident the raw CNN already is (e.g., on clean PlantVillage leaves)
        base_probs = torch.softmax(combined_logits / 0.65, dim=0)
        max_base_prob = float(base_probs.max().item())

        # Build symptom & crop adjustment in logit space when the sample is a vegetable/fruit
        # or has non-studio background where raw 38-class softmax is diluted
        bonus = torch.zeros(num_classes, dtype=combined_logits.dtype, device=combined_logits.device)
        sev = fg_info["symptom_severity"]
        nec = fg_info["necrotic_ratio"]
        yel = fg_info["yellow_ratio"]
        rst = fg_info["rust_ratio"]
        pwd = fg_info["powdery_ratio"]
        organ = fg_info["organ_type"]

        for idx, c_info in enumerate(classes_meta):
            d_key = (c_info.get("disease_key") or "").lower()
            is_healthy_cls = bool(c_info.get("healthy"))

            # Symptom alignment bonus for non-studio / vegetable / field images
            if is_healthy_cls:
                if sev < 0.14 and nec < 0.025:
                    bonus[idx] += 1.35
                elif sev > 0.28 or nec > 0.06:
                    bonus[idx] -= 1.60
            else:
                if sev >= 0.22:
                    bonus[idx] += 0.65
                if nec >= 0.04 and any(k in d_key for k in ("blight", "rot", "spot", "scab", "scorch")):
                    bonus[idx] += 1.10
                if yel >= 0.05 and any(k in d_key for k in ("yellow", "mosaic", "greening", "mold", "blight")):
                    bonus[idx] += 0.95
                if rst >= 0.03 and "rust" in d_key:
                    bonus[idx] += 1.20
                if pwd >= 0.04 and ("powdery" in d_key or "mildew" in d_key):
                    bonus[idx] += 1.20

            # If user selected a supported crop AND either:
            # - the sample is a vegetable/fruit (where leaf-shape cues are absent), OR
            # - raw global leaf confidence is moderate/low (< 0.62) due to field background
            if selected_crop_key and c_info.get("crop_key") == selected_crop_key:
                if organ == "vegetable_or_fruit":
                    bonus[idx] += 2.60
                elif max_base_prob < 0.68:
                    bonus[idx] += 1.65

        # Blend strength: if raw CNN is already highly confident (>0.78 on a clean leaf),
        # barely touch it; otherwise apply the symptom + crop calibration
        alpha = 0.15 if max_base_prob >= 0.78 else (0.85 if organ == "vegetable_or_fruit" else 0.65)
        calibrated_logits = (combined_logits + alpha * bonus) / 0.55
        return torch.softmax(calibrated_logits, dim=0)

    def predict(self, image: Image.Image, top_k: int = 3, selected_crop_key: Optional[str] = None):
        """Return the top-k (class_index, probability) pairs for a PIL image."""
        import torch
        self._load()
        fg_info = analyze_foreground_and_symptoms(image)
        batch = torch.stack([
            self._full_transform(image),
            self._transform(image),
            self._full_transform(fg_info["roi_img"]),
            self._full_transform(fg_info["lesion_patch_img"]),
        ], dim=0).to(self._device)
        with torch.no_grad():
            raw_logits = self._model(batch)
            probs = self._compute_calibrated_probs(raw_logits, fg_info, selected_crop_key).cpu()
        values, indices = probs.topk(min(top_k, probs.numel()))
        return [(int(i), float(v)) for v, i in zip(values, indices)]

    def predict_with_gradcam(
        self,
        image: Image.Image,
        top_k: int = 3,
        selected_crop_key: Optional[str] = None,
    ) -> dict:
        """
        Run 4-view inference + organ/lesion calibration and compute a Grad-CAM
        visual explanation heatmap highlighting the leaf or vegetable regions
        that drove the diagnosis.
        """
        import torch
        self._load()
        fg_info = analyze_foreground_and_symptoms(image)

        activations = []
        gradients = []
        target_layer = self._model.features[-1]

        def fwd_hook(_module, _inp, out):
            activations.append(out.detach())

        def bwd_hook(_module, _grad_in, grad_out):
            gradients.append(grad_out[0].detach())

        with self._lock:
            h1 = target_layer.register_forward_hook(fwd_hook)
            h2 = target_layer.register_full_backward_hook(bwd_hook)
            try:
                x_other = torch.stack([
                    self._transform(image),
                    self._full_transform(fg_info["roi_img"]),
                    self._full_transform(fg_info["lesion_patch_img"]),
                ], dim=0).to(self._device)
                with torch.no_grad():
                    logits_other = self._model(x_other)

                x_full = self._full_transform(image).unsqueeze(0).to(self._device)
                x_full.requires_grad_(True)
                self._model.zero_grad()
                logits_full = self._model(x_full)

                all_logits = torch.cat([logits_full.detach(), logits_other], dim=0)
                probs = self._compute_calibrated_probs(all_logits, fg_info, selected_crop_key)
                values, indices = probs.topk(min(top_k, probs.numel()))
                top_idx = int(indices[0].item())
                logits_full[0, top_idx].backward()
            finally:
                h1.remove()
                h2.remove()

        top_pairs = [(int(i), float(v)) for v, i in zip(values.detach().cpu(), indices.detach().cpu())]

        # Compute Grad-CAM from captured feature maps and gradients
        act = activations[0][0]      # [C, H, W]
        grad = gradients[0][0]       # [C, H, W]
        weights = grad.mean(dim=(1, 2), keepdim=True)
        cam = torch.relu((weights * act).sum(dim=0)).cpu().numpy()

        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        else:
            cam = np.zeros_like(cam)

        # Resize original image, Grad-CAM, and surface lesion saliency to 280x280
        disp_size = (280, 280)
        base_img = image.convert("RGB").resize(disp_size, Image.Resampling.BILINEAR)
        cam_img = Image.fromarray((cam * 255).astype(np.uint8)).resize(disp_size, Image.Resampling.BILINEAR)
        cam_resized = np.asarray(cam_img, dtype=np.float32) / 255.0

        lesion_img = Image.fromarray((fg_info["lesion_map_224"] * 255).astype(np.uint8)).resize(
            disp_size, Image.Resampling.BILINEAR
        )
        lesion_resized = np.asarray(lesion_img, dtype=np.float32) / 255.0

        # Fuse coarse 7x7 CNN Grad-CAM with fine-grained surface lesion saliency
        if fg_info["symptom_severity"] >= 0.18:
            fused_cam = 0.55 * cam_resized + 0.45 * lesion_resized
            if fused_cam.max() > fused_cam.min():
                fused_cam = (fused_cam - fused_cam.min()) / (fused_cam.max() - fused_cam.min())
            cam_resized = fused_cam

        heat_rgb = _apply_jet_colormap(cam_resized)
        base_rgb = np.asarray(base_img, dtype=np.float32)

        alpha = (0.18 + 0.52 * cam_resized)[..., None]
        blended = np.clip(base_rgb * (1.0 - alpha) + heat_rgb * alpha, 0, 255).astype(np.uint8)
        overlay_img = Image.fromarray(blended)

        hotspot_pct = round(float((cam_resized >= 0.55).mean() * 100.0), 1)

        return {
            "top_pairs": top_pairs,
            "organ_type": fg_info["organ_type"],
            "symptom_severity": fg_info["symptom_severity"],
            "original_data_uri": _pil_to_data_uri(base_img),
            "gradcam_data_uri": _pil_to_data_uri(overlay_img),
            "hotspot_coverage_pct": hotspot_pct,
        }


predictor = CropDiseasePredictor()

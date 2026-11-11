"""
Model architecture definitions (shared by training and inference).

We use transfer learning: a small network pretrained on ImageNet whose final
layer is replaced with one output per crop/disease class.
"""

SUPPORTED_ARCHS = ["mobilenet_v3_large", "mobilenet_v3_small", "efficientnet_b0"]


def build_model(arch: str, num_classes: int, pretrained: bool = True):
    import torch.nn as nn
    from torchvision import models

    if arch == "mobilenet_v3_large":
        weights = models.MobileNet_V3_Large_Weights.IMAGENET1K_V2 if pretrained else None
        model = models.mobilenet_v3_large(weights=weights)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    elif arch == "mobilenet_v3_small":
        weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.mobilenet_v3_small(weights=weights)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    elif arch == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    else:
        raise ValueError(f"Unknown architecture '{arch}'. Choose from {SUPPORTED_ARCHS}.")
    return model


def backbone_parameters(model):
    """Parameters of the pretrained feature extractor (frozen in phase 1)."""
    return model.features.parameters()

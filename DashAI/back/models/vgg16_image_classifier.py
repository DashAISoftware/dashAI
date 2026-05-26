"""VGG-16 image classifier for DashAI."""

import torch.nn as nn
from torchvision.models import VGG16_Weights, vgg16

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_torchvision_image_classifier import (
    TorchvisionImageClassifier,
    TorchvisionImageClassifierSchema,
)


class VGG16ImageClassifier(TorchvisionImageClassifier):
    """VGG-16 image classifier (Simonyan & Zisserman, 2014).

    16-layer deep network using exclusively 3×3 convolutions. The classifier
    head (last FC layer) is replaced to match the number of target classes.
    Supports ImageNet pre-trained weights for transfer learning.
    """

    SCHEMA = TorchvisionImageClassifierSchema
    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="VGG-16",
        es="VGG-16",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "VGG-16 (Simonyan & Zisserman, 2014). A 16-layer deep network "
            "built exclusively with 3×3 convolutions. Standard academic "
            "baseline; supports ImageNet pre-trained weights."
        ),
        es=(
            "VGG-16 (Simonyan & Zisserman, 2014). Red profunda de 16 capas "
            "construida exclusivamente con convoluciones 3×3. Baseline académico "
            "estándar; soporta pesos preentrenados en ImageNet."
        ),
    )
    COLOR: str = "#E65100"
    ICON: str = "AccountTree"

    def _build_backbone(self, num_classes: int, pretrained: bool) -> nn.Module:
        weights = VGG16_Weights.DEFAULT if pretrained else None
        model = vgg16(weights=weights)
        model.classifier[6] = nn.Sequential(
            nn.Dropout(self.dropout_rate),
            nn.Linear(4096, num_classes),
        )
        return model

    def _classifier_head(self) -> nn.Module:
        return self.model.classifier

"""ResNet-50 image classifier for DashAI."""

import torch.nn as nn
from torchvision.models import ResNet50_Weights, resnet50

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_torchvision_image_classifier import (
    TorchvisionImageClassifier,
    TorchvisionImageClassifierSchema,
)


class ResNet50ImageClassifier(TorchvisionImageClassifier):
    """ResNet-50 image classifier (He et al., 2015).

    50-layer residual network using bottleneck blocks. Deeper and more
    accurate than ResNet-18, and the most-cited CNN variant in the academic
    literature. The final FC layer is replaced to match the target classes.
    Supports ImageNet pre-trained weights.
    """

    SCHEMA = TorchvisionImageClassifierSchema
    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="ResNet-50",
        es="ResNet-50",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "ResNet-50 (He et al., 2015). A 50-layer residual network with "
            "bottleneck blocks and skip connections. The most-cited CNN variant "
            "in academic papers; supports ImageNet pre-trained weights."
        ),
        es=(
            "ResNet-50 (He et al., 2015). Red residual de 50 capas con bloques "
            "bottleneck y conexiones de salto. La variante CNN más citada en "
            "papers académicos; soporta pesos preentrenados en ImageNet."
        ),
    )
    COLOR: str = "#1B5E20"
    ICON: str = "AccountTree"

    def _build_backbone(self, num_classes: int, pretrained: bool) -> nn.Module:
        weights = ResNet50_Weights.DEFAULT if pretrained else None
        model = resnet50(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(self.dropout_rate),
            nn.Linear(in_features, num_classes),
        )
        return model

    def _classifier_head(self) -> nn.Module:
        return self.model.fc

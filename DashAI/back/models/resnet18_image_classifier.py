"""ResNet-18 image classifier for DashAI."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_torchvision_image_classifier import (
    TorchvisionImageClassifier,
    TorchvisionImageClassifierSchema,
)


class ResNet18ImageClassifier(TorchvisionImageClassifier):
    """ResNet-18 image classifier (He et al., 2015).

    18-layer residual network with skip connections that solve the vanishing
    gradient problem. The final fully-connected layer is replaced to match the
    number of target classes. Supports ImageNet pre-trained weights.
    """

    SCHEMA = TorchvisionImageClassifierSchema
    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="ResNet-18",
        es="ResNet-18",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "ResNet-18 (He et al., 2015). An 18-layer residual network with "
            "skip connections that enable training very deep networks. "
            "The most-cited CNN in academic literature."
        ),
        es=(
            "ResNet-18 (He et al., 2015). Red residual de 18 capas con "
            "conexiones de salto que permiten entrenar redes muy profundas. "
            "La CNN más citada en la literatura académica."
        ),
    )
    COLOR: str = "#2E7D32"
    ICON: str = "AccountTree"

    def _build_backbone(self, num_classes: int, pretrained: bool):
        import torch.nn as nn
        from torchvision.models import ResNet18_Weights, resnet18

        weights = ResNet18_Weights.DEFAULT if pretrained else None
        model = resnet18(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(self.dropout_rate),
            nn.Linear(in_features, num_classes),
        )
        return model

    def _classifier_head(self):
        return self.model.fc

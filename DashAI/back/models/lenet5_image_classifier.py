"""LeNet-5 image classifier for DashAI."""

from __future__ import annotations

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


class LeNet5ImageClassifierSchema(BaseSchema):
    """Configuration parameters for the LeNet-5 Image Classifier."""

    epochs: schema_field(
        int_field(ge=1),
        placeholder=10,
        description=MultilingualString(
            en=(
                "The number of epochs to train the model. An epoch is a full "
                "iteration over the training data."
            ),
            es=(
                "El número de épocas para entrenar el modelo. Una época es una "
                "iteración completa sobre los datos de entrenamiento."
            ),
            pt=(
                "O número de épocas para treinar o modelo. Uma época é uma "
                "iteração completa sobre os dados de treinamento."
            ),
        ),
        alias=MultilingualString(en="Epochs", es="Épocas", pt="Épocas"),
    )  # type: ignore

    learning_rate: schema_field(
        float_field(gt=0.0),
        placeholder=0.001,
        description=MultilingualString(
            en="Learning rate for the Adam optimizer.",
            es="Tasa de aprendizaje para el optimizador Adam.",
            pt="Taxa de aprendizado para o otimizador Adam.",
        ),
        alias=MultilingualString(
            en="Learning rate",
            es="Tasa de aprendizaje",
            pt="Taxa de aprendizado",
        ),
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1),
        placeholder=32,
        description=MultilingualString(
            en=(
                "Number of images processed together in each training step. "
                "Larger values speed up training but require more memory."
            ),
            es=(
                "Número de imágenes procesadas juntas en cada paso de "
                "entrenamiento. Valores más grandes aceleran el entrenamiento "
                "pero requieren más memoria."
            ),
            pt=(
                "Número de imagens processadas juntas em cada etapa de "
                "treinamento. Valores maiores aceleram o treinamento "
                "mas requerem mais memória."
            ),
        ),
        alias=MultilingualString(
            en="Batch size", es="Tamaño de lote", pt="Tamanho do lote"
        ),
    )  # type: ignore

    image_size: schema_field(
        int_field(ge=16),
        placeholder=32,
        description=MultilingualString(
            en=(
                "Images are resized to this value (in pixels) for both width "
                "and height. The original LeNet-5 uses 32×32."
            ),
            es=(
                "Las imágenes se redimensionan a este valor (en píxeles) tanto "
                "en ancho como en alto. El LeNet-5 original usa 32×32."
            ),
            pt=(
                "As imagens são redimensionadas para este valor (em pixels) tanto "
                "em largura quanto em altura. O LeNet-5 original usa 32×32."
            ),
        ),
        alias=MultilingualString(
            en="Image size", es="Tamaño de imagen", pt="Tamanho da imagem"
        ),
    )  # type: ignore

    dropout_rate: schema_field(
        float_field(ge=0.0, lt=1.0),
        placeholder=0.0,
        description=MultilingualString(
            en=(
                "Dropout rate applied between fully-connected layers. "
                "Values between 0.2 and 0.5 help prevent overfitting. "
                "Use 0.0 to reproduce the original LeNet-5."
            ),
            es=(
                "Tasa de dropout entre las capas completamente conectadas. "
                "Valores entre 0.2 y 0.5 ayudan a prevenir el sobreajuste. "
                "Use 0.0 para reproducir el LeNet-5 original."
            ),
            pt=(
                "Taxa de dropout aplicada entre as camadas completamente conectadas. "
                "Valores entre 0.2 e 0.5 ajudam a prevenir o sobreajuste. "
                "Use 0.0 para reproduzir o LeNet-5 original."
            ),
        ),
        alias=MultilingualString(
            en="Dropout rate", es="Tasa de dropout", pt="Taxa de dropout"
        ),
    )  # type: ignore

    weight_decay: schema_field(
        float_field(ge=0.0),
        placeholder=0.0,
        description=MultilingualString(
            en=(
                "L2 regularization coefficient for the Adam optimizer. "
                "Typical values: 1e-4 to 1e-2."
            ),
            es=(
                "Coeficiente de regularización L2 para el optimizador Adam. "
                "Valores típicos: 1e-4 a 1e-2."
            ),
            pt=(
                "Coeficiente de regularização L2 para o otimizador Adam. "
                "Valores típicos: 1e-4 a 1e-2."
            ),
        ),
        alias=MultilingualString(
            en="Weight decay", es="Decaimiento de pesos", pt="Decaimento de pesos"
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en="Hardware device used for training and inference (CPU/GPU).",
            es="Dispositivo de hardware para entrenamiento e inferencia (CPU/GPU).",
            pt="Dispositivo de hardware usado para treinamento e inferência (CPU/GPU).",
        ),
        alias=MultilingualString(en="Device", es="Dispositivo", pt="Dispositivo"),
    )  # type: ignore


def _make_image_dataset(x_dataset, y_dataset=None, image_size=32):
    import torch.utils.data
    from torchvision import transforms

    class _ImageDataset(torch.utils.data.Dataset):
        def __init__(self, x_ds, y_ds, img_size):
            self.x_dataset = x_ds
            self.y_dataset = y_ds
            self.transforms = transforms.Compose(
                [
                    transforms.Resize((img_size, img_size)),
                    transforms.ToTensor(),
                ]
            )

            self.image_col_name = list(x_ds.features.keys())[0]
            self.label_col_name = (
                list(y_ds.features.keys())[0] if y_ds is not None else None
            )

            self.label_to_idx = {}
            self.idx_to_label = {}
            if self.label_col_name:
                unique_labels = sorted(set(self.y_dataset[self.label_col_name]))
                self.label_to_idx = {
                    label: idx for idx, label in enumerate(unique_labels)
                }
                self.idx_to_label = {
                    idx: label for label, idx in self.label_to_idx.items()
                }

            self.tensor_shape = self.transforms(
                self.x_dataset[0][self.image_col_name].to_pil()
            ).shape

        def num_classes(self):
            if self.label_col_name is None:
                return 0
            return len(self.label_to_idx)

        def __len__(self):
            return len(self.x_dataset)

        def __getitem__(self, idx):
            image = self.transforms(self.x_dataset[idx][self.image_col_name].to_pil())
            if self.label_col_name is None:
                return image
            label_str = self.y_dataset[idx][self.label_col_name]
            return image, self.label_to_idx[label_str]

    return _ImageDataset(x_dataset, y_dataset, image_size)


def _build_lenet5_model(input_channels, input_size, num_classes, dropout_rate):
    import torch
    import torch.nn as nn

    class _LeNet5(nn.Module):
        def __init__(self, in_ch, in_sz, n_cls, drop_r):
            super().__init__()
            self.conv_layers = nn.Sequential(
                nn.Conv2d(in_ch, 6, kernel_size=5),
                nn.Tanh(),
                nn.AvgPool2d(kernel_size=2, stride=2),
                nn.Conv2d(6, 16, kernel_size=5),
                nn.Tanh(),
                nn.AvgPool2d(kernel_size=2, stride=2),
            )

            dummy = torch.zeros(1, in_ch, in_sz, in_sz)
            flat_dim = self.conv_layers(dummy).view(1, -1).shape[1]

            self.classifier = nn.Sequential(
                nn.Linear(flat_dim, 120),
                nn.Tanh(),
                nn.Dropout(drop_r),
                nn.Linear(120, 84),
                nn.Tanh(),
                nn.Dropout(drop_r),
                nn.Linear(84, n_cls),
            )

        def forward(self, x):
            x = self.conv_layers(x)
            return self.classifier(x.view(x.size(0), -1))

    return _LeNet5(input_channels, input_size, num_classes, dropout_rate)


class LeNet5ImageClassifier(BaseModel):
    """LeNet-5 image classifier (LeCun et al., 1998).

    The original convolutional neural network architecture, featuring two
    conv→tanh→pool blocks followed by three fully-connected layers.
    Uses Tanh activations and average pooling as in the original paper.
    """

    SCHEMA = LeNet5ImageClassifierSchema
    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="LeNet-5",
        es="LeNet-5",
        pt="LeNet-5",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "The original CNN architecture (LeCun et al., 1998). Two "
            "conv→tanh→pool blocks followed by three fully-connected layers. "
            "Ideal for small images and educational use."
        ),
        es=(
            "La arquitectura CNN original (LeCun et al., 1998). Dos bloques "
            "conv→tanh→pool seguidos de tres capas completamente conectadas. "
            "Ideal para imágenes pequeñas y uso educativo."
        ),
        pt=(
            "A arquitetura CNN original (LeCun et al., 1998). Dois blocos "
            "conv→tanh→pool seguidos de três camadas completamente conectadas. "
            "Ideal para imagens pequenas e uso educacional."
        ),
    )
    COLOR: str = "#7B1FA2"
    ICON: str = "History"

    @staticmethod
    def _collate_fn_with_labels(batch):
        import torch

        images = torch.stack([item[0] for item in batch])
        labels = torch.tensor([item[1] for item in batch], dtype=torch.long)
        return images, labels

    @staticmethod
    def _collate_fn_no_labels(batch):
        import torch

        return torch.stack(batch)

    def __init__(
        self,
        epochs=10,
        learning_rate=0.001,
        batch_size=32,
        image_size=32,
        dropout_rate=0.0,
        weight_decay=0.0,
        device=DEVICE_PLACEHOLDER,
        **kwargs,
    ):
        import torch

        self.epochs = epochs
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.image_size = image_size
        self.dropout_rate = dropout_rate
        self.weight_decay = weight_decay
        self._device_name = device
        self.device = torch.device(
            f"cuda:{DEVICE_TO_IDX.get(device)}"
            if DEVICE_TO_IDX.get(device, -1) >= 0
            else "cpu"
        )
        self.model = None
        self.optimizer = None
        self.input_channels = None
        self.num_classes = None
        self.idx_to_label = {}
        self.label_to_idx = {}

    def prepare_output(self, dataset, is_fit=False):
        """Encode string labels to integer indices matching the model's class order."""
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        if not self.label_to_idx:
            return dataset

        col_name = dataset.column_names[0]
        encoded = [self.label_to_idx.get(lbl, lbl) for lbl in dataset[col_name]]
        return DashAIDataset(pa.table({col_name: encoded}))

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        """Train LeNet-5 on the provided image dataset.

        Parameters
        ----------
        x_train : DashAIDataset
            Input dataset containing images.
        y_train : DashAIDataset
            Target dataset containing string labels.
        x_validation : DashAIDataset, optional
            Validation input features. Defaults to None.
        y_validation : DashAIDataset, optional
            Validation target labels. Defaults to None.

        Returns
        -------
        LeNet5ImageClassifier
            The trained model instance.
        """
        import torch
        import torch.nn as nn
        import torch.optim as optim
        import torch.utils.data

        from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum

        image_dataset = _make_image_dataset(
            x_train, y_dataset=y_train, image_size=self.image_size
        )
        self.input_channels = image_dataset.tensor_shape[0]
        self.num_classes = image_dataset.num_classes()
        self.idx_to_label = image_dataset.idx_to_label
        self.label_to_idx = image_dataset.label_to_idx

        train_loader = torch.utils.data.DataLoader(
            image_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=self._collate_fn_with_labels,
        )

        self.model = _build_lenet5_model(
            self.input_channels,
            self.image_size,
            self.num_classes,
            self.dropout_rate,
        ).to(self.device)

        criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )

        for epoch in range(self.epochs):
            self.model.train()
            for images, labels in train_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                self.optimizer.zero_grad()
                loss = criterion(self.model(images), labels)
                loss.backward()
                self.optimizer.step()

            self.model.eval()
            self.calculate_metrics(
                split=SplitEnum.TRAIN,
                level=LevelEnum.EPOCH,
                x_data=x_train,
                y_data=y_train,
                log_index=epoch + 1,
            )
            if x_validation is not None:
                self.calculate_metrics(
                    split=SplitEnum.VALIDATION,
                    level=LevelEnum.EPOCH,
                    x_data=x_validation,
                    y_data=y_validation,
                    log_index=epoch + 1,
                )

        return self

    def predict(self, x):
        """Return per-class probability matrix for each image.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset containing images.

        Returns
        -------
        np.ndarray
            Array of shape (n_samples, n_classes) with softmax probabilities.
        """
        import numpy as np
        import torch
        import torch.utils.data

        image_dataset = _make_image_dataset(
            x, y_dataset=None, image_size=self.image_size
        )
        loader = torch.utils.data.DataLoader(
            image_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=self._collate_fn_no_labels,
        )

        self.model.to(self.device)
        self.model.eval()
        all_probs = []
        with torch.no_grad():
            for images in loader:
                logits = self.model(images.to(self.device))
                all_probs.append(torch.softmax(logits, dim=1).cpu().numpy())

        return np.concatenate(all_probs, axis=0)

    def save(self, filename: str) -> None:
        """Save the model checkpoint to disk.

        Parameters
        ----------
        filename : str
            Path where the checkpoint will be saved.
        """
        import torch

        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "epochs": self.epochs,
                "learning_rate": self.learning_rate,
                "batch_size": self.batch_size,
                "image_size": self.image_size,
                "dropout_rate": self.dropout_rate,
                "weight_decay": self.weight_decay,
                "device_name": self._device_name,
                "input_channels": self.input_channels,
                "num_classes": self.num_classes,
                "idx_to_label": self.idx_to_label,
                "label_to_idx": self.label_to_idx,
            },
            filename,
        )

    @classmethod
    def load(cls, filename: str):
        """Load a model checkpoint from disk.

        Parameters
        ----------
        filename : str
            Path to the checkpoint file.

        Returns
        -------
        LeNet5ImageClassifier
            Instance with loaded weights.
        """
        import torch
        import torch.optim as optim

        ckpt = torch.load(filename, map_location=torch.device("cpu"))
        instance = cls(
            epochs=ckpt["epochs"],
            learning_rate=ckpt["learning_rate"],
            batch_size=ckpt.get("batch_size", 32),
            image_size=ckpt.get("image_size", 32),
            dropout_rate=ckpt.get("dropout_rate", 0.0),
            weight_decay=ckpt.get("weight_decay", 0.0),
            device=ckpt.get("device_name", DEVICE_PLACEHOLDER),
        )
        instance.input_channels = ckpt["input_channels"]
        instance.num_classes = ckpt["num_classes"]
        instance.idx_to_label = ckpt.get("idx_to_label", {})
        instance.label_to_idx = ckpt.get("label_to_idx", {})
        instance.model = _build_lenet5_model(
            instance.input_channels,
            instance.image_size,
            instance.num_classes,
            instance.dropout_rate,
        )
        instance.model.load_state_dict(ckpt["model_state_dict"])
        instance.optimizer = optim.Adam(
            instance.model.parameters(),
            weight_decay=instance.weight_decay,
        )
        instance.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        return instance

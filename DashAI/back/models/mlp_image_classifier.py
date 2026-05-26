"""MLP-based image classifier for DashAI."""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data
from torchvision import transforms

from DashAI.back.core.schema_fields import (
    BaseSchema,
    float_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_model import BaseModel


class MLPImageClassifierSchema(BaseSchema):
    """Configuration parameters for the MLP Image Classifier."""

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
        ),
        alias=MultilingualString(en="Epochs", es="Épocas"),
    )  # type: ignore

    learning_rate: schema_field(
        float_field(gt=0.0),
        placeholder=0.001,
        description=MultilingualString(
            en="Learning rate for the Adam optimizer.",
            es="Tasa de aprendizaje para el optimizador Adam.",
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
    )  # type: ignore

    hidden_dims: schema_field(
        list_field(int_field(ge=1), min_items=1),
        placeholder=[128, 64],
        description=MultilingualString(
            en=(
                "The hidden layers and their dimensions. Specify the number "
                "of units of each layer separated by commas."
            ),
            es=(
                "Las capas ocultas y sus dimensiones. Especifique el número "
                "de unidades de cada capa separadas por comas."
            ),
        ),
        alias=MultilingualString(
            en="Hidden layer dimensions",
            es="Dimensiones de capas ocultas",
        ),
    )  # type: ignore


class _ImageDataset(torch.utils.data.Dataset):
    """Torch Dataset wrapper for DashAI image datasets."""

    def __init__(self, x_dataset, y_dataset=None):
        self.x_dataset = x_dataset
        self.y_dataset = y_dataset
        self.transforms = transforms.Compose(
            [
                transforms.Resize((30, 30)),
                transforms.ToTensor(),
            ]
        )

        self.image_col_name = list(x_dataset.features.keys())[0]
        self.label_col_name = (
            list(y_dataset.features.keys())[0] if y_dataset is not None else None
        )

        self.label_to_idx = {}
        self.idx_to_label = {}
        if self.label_col_name:
            unique_labels = sorted(set(self.y_dataset[self.label_col_name]))
            self.label_to_idx = {label: idx for idx, label in enumerate(unique_labels)}
            self.idx_to_label = {idx: label for label, idx in self.label_to_idx.items()}

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
        label_idx = self.label_to_idx[label_str]
        return image, label_idx


class _MLP(nn.Module):
    """Multi-Layer Perceptron for image classification."""

    def __init__(self, input_dim, output_dim, hidden_dims):
        super().__init__()
        self.hidden_layers = nn.ModuleList()
        previous_dim = input_dim

        for hidden_dim in hidden_dims:
            self.hidden_layers.append(nn.Linear(previous_dim, hidden_dim))
            previous_dim = hidden_dim

        self.output_layer = nn.Linear(previous_dim, output_dim)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor):
        batch_size = x.shape[0]
        x = x.view(batch_size, -1)

        for layer in self.hidden_layers:
            x = self.relu(layer(x))

        return self.output_layer(x)


class MLPImageClassifier(BaseModel):
    """MLP-based image classifier.

    A feed-forward neural network that flattens image pixels and passes them
    through configurable hidden layers with ReLU activation for classification.
    """

    SCHEMA = MLPImageClassifierSchema
    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="MLP Image Classifier",
        es="Clasificador de Imágenes MLP",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "A Multi-Layer Perceptron (MLP) image classifier that flattens "
            "image pixels and passes them through configurable fully-connected "
            "hidden layers with ReLU activation for classification."
        ),
        es=(
            "Un clasificador de imágenes basado en Perceptrón Multicapa (MLP) "
            "que aplana los píxeles de la imagen y los pasa por capas ocultas "
            "completamente conectadas con activación ReLU para clasificación."
        ),
    )
    COLOR: str = "#E91E63"
    ICON: str = "ImageSearch"

    @staticmethod
    def _collate_fn_with_labels(batch):
        """Custom collate function for batches with (image, label) tuples."""
        images = torch.stack([item[0] for item in batch])
        labels = torch.tensor([item[1] for item in batch], dtype=torch.long)
        return images, labels

    @staticmethod
    def _collate_fn_no_labels(batch):
        """Custom collate function for batches with only images."""
        return torch.stack(batch)

    def __init__(self, epochs=10, learning_rate=0.001, hidden_dims=None, **kwargs):
        if hidden_dims is None:
            hidden_dims = [128, 64]
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.hidden_dims = hidden_dims
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.optimizer = None
        self.input_dim = None
        self.output_dim = None
        self.idx_to_label = {}
        self.label_to_idx = {}

    def prepare_output(self, dataset, is_fit=False):
        """Encode string labels to integer indices matching the model's class order."""
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        if not self.label_to_idx:
            return dataset

        col_name = dataset.column_names[0]
        labels = dataset[col_name]
        encoded = [self.label_to_idx.get(label, label) for label in labels]
        table = pa.table({col_name: encoded})
        return DashAIDataset(table)

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        """Train the MLP on the provided image dataset.

        Parameters
        ----------
        x_train : DashAIDataset
            Input dataset containing images.
        y_train : DashAIDataset
            Target dataset containing labels.
        x_validation : DashAIDataset, optional
            Validation input features (unused). Defaults to None.
        y_validation : DashAIDataset, optional
            Validation target labels (unused). Defaults to None.

        Returns
        -------
        MLPImageClassifier
            The trained model instance.
        """
        image_dataset = _ImageDataset(x_train, y_dataset=y_train)

        self.input_dim = (
            image_dataset.tensor_shape[0]
            * image_dataset.tensor_shape[1]
            * image_dataset.tensor_shape[2]
        )
        self.output_dim = image_dataset.num_classes()

        self.idx_to_label = image_dataset.idx_to_label
        self.label_to_idx = image_dataset.label_to_idx

        train_loader = torch.utils.data.DataLoader(
            image_dataset,
            batch_size=32,
            shuffle=True,
            collate_fn=self._collate_fn_with_labels,
        )

        self.model = _MLP(self.input_dim, self.output_dim, self.hidden_dims).to(
            self.device
        )
        criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

        self.model.train()
        for _ in range(self.epochs):
            for images, labels in train_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                self.optimizer.zero_grad()
                outputs = self.model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()

        return self

    def predict(self, x):
        """Make predictions on the input dataset.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset containing images.

        Returns
        -------
        list of lists
            List of predicted probabilities for each class for each image.
        """
        image_dataset = _ImageDataset(x, y_dataset=None)
        test_loader = torch.utils.data.DataLoader(
            image_dataset,
            batch_size=32,
            shuffle=False,
            collate_fn=self._collate_fn_no_labels,
        )

        self.model.eval()
        all_probs = []
        with torch.no_grad():
            for images in test_loader:
                images = images.to(self.device)
                logits = self.model(images)
                probs = torch.softmax(logits, dim=1)
                all_probs += probs.cpu().tolist()

        return all_probs

    def save(self, filename: str) -> None:
        """Save the model checkpoint to disk.

        Parameters
        ----------
        filename : str
            Path where the checkpoint will be saved.
        """
        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "hidden_dims": self.hidden_dims,
            "input_dim": self.input_dim,
            "output_dim": self.output_dim,
            "idx_to_label": self.idx_to_label,
            "label_to_idx": self.label_to_idx,
        }
        torch.save(checkpoint, filename)

    @classmethod
    def load(cls, filename: str):
        """Load a model checkpoint from disk.

        Parameters
        ----------
        filename : str
            Path to the checkpoint file.

        Returns
        -------
        MLPImageClassifier
            Instance with loaded weights.
        """
        checkpoint = torch.load(filename, map_location=torch.device("cpu"))
        instance = cls(
            epochs=checkpoint["epochs"],
            learning_rate=checkpoint["learning_rate"],
            hidden_dims=checkpoint["hidden_dims"],
        )
        instance.input_dim = checkpoint["input_dim"]
        instance.output_dim = checkpoint["output_dim"]
        instance.model = _MLP(
            instance.input_dim, instance.output_dim, instance.hidden_dims
        )
        instance.model.load_state_dict(checkpoint["model_state_dict"])
        instance.optimizer = optim.Adam(instance.model.parameters())
        instance.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        instance.idx_to_label = checkpoint.get("idx_to_label", {})
        instance.label_to_idx = checkpoint.get("label_to_idx", {})
        return instance

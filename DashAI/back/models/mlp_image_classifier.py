"""MLP-based image classifier for DashAI."""

import datasets
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
    """Torch Dataset wrapper for HuggingFace image datasets."""

    def __init__(self, hf_dataset: datasets.Dataset, has_labels: bool = True):
        self.dataset = hf_dataset
        self.has_labels = has_labels
        self.transforms = transforms.Compose(
            [
                transforms.Resize((30, 30)),
                transforms.ToTensor(),
            ]
        )

        column_names = list(self.dataset.features.keys())
        self.image_col_name = column_names[0]
        self.label_col_name = (
            column_names[1] if has_labels and len(column_names) > 1 else None
        )

        self.tensor_shape = self.transforms(self.dataset[0][self.image_col_name]).shape

    def num_classes(self):
        if self.label_col_name is None:
            return 0
        return len(set(self.dataset[self.label_col_name]))

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        image = self.transforms(self.dataset[idx][self.image_col_name])
        if self.label_col_name is None:
            return image
        label = self.dataset[idx][self.label_col_name]
        return image, label


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
    ICON: str = "Image"

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
        image_col = list(x_train.features.keys())[0]
        label_col = list(y_train.features.keys())[0]

        hf_dataset = datasets.Dataset.from_dict(
            {
                "image": x_train[image_col],
                "label": y_train[label_col],
            }
        )
        image_dataset = _ImageDataset(hf_dataset, has_labels=True)

        self.input_dim = (
            image_dataset.tensor_shape[0]
            * image_dataset.tensor_shape[1]
            * image_dataset.tensor_shape[2]
        )
        self.output_dim = image_dataset.num_classes()

        train_loader = torch.utils.data.DataLoader(
            image_dataset, batch_size=32, shuffle=True
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
        list
            List of predicted probabilities for each class.
        """
        image_col = list(x.features.keys())[0]
        hf_dataset = datasets.Dataset.from_dict({"image": x[image_col]})
        image_dataset = _ImageDataset(hf_dataset, has_labels=False)
        test_loader = torch.utils.data.DataLoader(
            image_dataset, batch_size=32, shuffle=False
        )

        self.model.eval()
        probs_predicted = []
        with torch.no_grad():
            for images in test_loader:
                images = images.to(self.device)
                output_probs = self.model(images)
                probs_predicted += output_probs.tolist()
        return probs_predicted

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
        return instance

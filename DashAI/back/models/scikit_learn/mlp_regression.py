import numpy as np
import torch
import torch.nn as nn

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


class MLPRegressorSchema(BaseSchema):
    """PyTorch MLP Regressor Schema."""

    hidden_size: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 1,
            "upper_bound": 15,
        },
        description="Number of neurons in the hidden layer.",
    )  # type: ignore

    activation: schema_field(
        enum_field(enum=["relu", "tanh", "sigmoid"]),
        placeholder="relu",
        description="Activation function.",
    )  # type: ignore

    learning_rate: schema_field(
        optimizer_float_field(ge=1e-6, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.001,
            "lower_bound": 1e-6,
            "upper_bound": 1.0,
        },
        description="Initial learning rate for the optimizer.",
    )  # type: ignore

    epochs: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 1,
            "upper_bound": 15,
        },
        description="Total number of training passes over the dataset.",
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description="Hardware device (CPU/GPU).",
    )  # type: ignore


class MLP(nn.Module):
    def __init__(self, input_dim, hidden_size, activation_name):
        super().__init__()
        activations = {
            "relu": nn.ReLU(),
            "tanh": nn.Tanh(),
            "logistic": nn.Sigmoid(),
            "identity": nn.Identity(),
        }
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_size),
            activations.get(activation_name, nn.ReLU()),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x):
        return self.model(x)


class MLPRegression(RegressionModel):
    SCHEMA = MLPRegressorSchema
    DISPLAY_NAME: str = "Multi-layer Perceptron (MLP) Regression"
    COLOR: str = "#FF7043"

    def __init__(self, **kwargs) -> None:
        self.params = kwargs
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}"
            if DEVICE_TO_IDX.get(kwargs.get("device"), -1) >= 0
            else "cpu"
        )
        self.model = None

    def train(
        self,
        x_train: DashAIDataset,
        y_train: DashAIDataset,
        x_validation: DashAIDataset = None,
        y_validation: DashAIDataset = None,
    ) -> "MLPRegression":
        # 1. Prepare Data
        x_values = self.prepare_dataset(x_train, is_fit=True).to_pandas().values
        y_values = self.prepare_output(y_train, is_fit=True).to_pandas().values

        X_tensor = torch.tensor(x_values, dtype=torch.float32).to(self.device)
        y_tensor = (
            torch.tensor(y_values, dtype=torch.float32).view(-1, 1).to(self.device)
        )

        # 2. Init Model & Optimizer
        self.model = MLP(
            input_dim=X_tensor.shape[1],
            hidden_size=self.params.get("hidden_size", 100),
            activation_name=self.params.get("activation", "relu"),
        ).to(self.device)

        optimizer = torch.optim.Adam(
            self.model.parameters(), lr=self.params.get("learning_rate", 0.001)
        )
        criterion = nn.MSELoss()

        # 3. Training Loop using Epochs
        total_epochs = self.params.get("epochs", 3)
        batch_size = min(200, X_tensor.size(0))

        for _ in range(total_epochs):
            self.model.train()
            indices = torch.randperm(X_tensor.size(0))

            for i in range(0, X_tensor.size(0), batch_size):
                batch_idx = indices[i : i + batch_size]
                train_loss = criterion(
                    self.model(X_tensor[batch_idx]), y_tensor[batch_idx]
                )

                optimizer.zero_grad()
                train_loss.backward()
                optimizer.step()

            # Metric tracking per epoch
            self.calculate_metrics(
                split=SplitEnum.TRAIN,
                level=LevelEnum.EPOCH,
                x_data=x_train,
                y_data=y_train,
            )

            self.calculate_metrics(
                split=SplitEnum.VALIDATION,
                level=LevelEnum.EPOCH,
                x_data=x_validation,
                y_data=y_validation,
            )

        return self

    def predict(self, x: DashAIDataset) -> np.ndarray:
        self.model.eval()
        x_proc = self.prepare_dataset(x, is_fit=False).to_pandas().values
        x_tensor = torch.tensor(x_proc, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            return self.model(x_tensor).cpu().numpy().flatten()

    def save(self, filename: str) -> None:
        torch.save(
            {
                "state": self.model.state_dict(),
                "params": self.params,
                "input_dim": self.model.model[0].in_features,
            },
            filename,
        )

    @staticmethod
    def load(filename: str) -> "MLPRegression":
        data = torch.load(filename)
        instance = MLPRegression(**data["params"])

        # Rebuild the model architecture using saved input_dim
        instance.model = MLP(
            input_dim=data["input_dim"],
            hidden_size=instance.params.get("hidden_size", 5),
            activation_name=instance.params.get("activation", "relu"),
        ).to(instance.device)

        # Load the trained weights
        instance.model.load_state_dict(data["state"])

        return instance

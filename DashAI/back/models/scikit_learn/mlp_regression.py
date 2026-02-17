import numpy as np
import torch
import torch.nn as nn

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
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
        description=MultilingualString(
            en="Number of neurons in the hidden layer.",
            es="Número de neuronas en la capa oculta.",
        ),
        alias=MultilingualString(en="Hidden size", es="Tamaño oculto"),
    )  # type: ignore

    activation: schema_field(
        enum_field(enum=["relu", "tanh", "sigmoid", "identity"]),
        placeholder="relu",
        description=MultilingualString(
            en="Activation function.",
            es="Función de activación.",
        ),
        alias=MultilingualString(en="Activation", es="Activación"),
    )  # type: ignore

    learning_rate: schema_field(
        optimizer_float_field(ge=1e-6, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.001,
            "lower_bound": 1e-6,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en="Initial learning rate for the optimizer.",
            es="Tasa de aprendizaje inicial para el optimizador.",
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
    )  # type: ignore

    epochs: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 1,
            "upper_bound": 15,
        },
        description=MultilingualString(
            en="Total number of training passes over the dataset.",
            es="Número total de pasadas de entrenamiento sobre el conjunto de datos.",
        ),
        alias=MultilingualString(en="Epochs", es="Épocas"),
    )  # type: ignore

    batch_size: schema_field(
        none_type(int_field(ge=1)),
        placeholder=32,
        description=MultilingualString(
            en=(
                "Number of samples per gradient update during training. "
                "If greater than dataset size or None, uses full dataset."
            ),
            es=(
                "Número de muestras por actualización de gradiente durante el "
                "entrenamiento. Si es mayor que el tamaño del dataset o None, "
                "usa el dataset completo."
            ),
        ),
        alias=MultilingualString(en="Batch size", es="Tamaño de lote"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en="Hardware device (CPU/GPU).",
            es="Dispositivo de hardware (CPU/GPU).",
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore

    log_train_every_n_epochs: schema_field(
        none_type(int_field(ge=1)),
        placeholder=1,
        description=MultilingualString(
            en=(
                "Log metrics for train split every n epochs during training. "
                "If None, it won't log per epoch."
            ),
            es=(
                "Registrar métricas del split de entrenamiento cada n épocas. "
                "Si es None, no registrará por época."
            ),
        ),
        alias=MultilingualString(
            en="Log train every N epochs", es="Registrar entrenamiento cada N épocas"
        ),
    )  # type: ignore

    log_train_every_n_steps: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Log metrics for train split every n steps during training. "
                "If None, it won't log per step."
            ),
            es=(
                "Registrar métricas del split de entrenamiento cada n pasos. "
                "Si es None, no registrará por paso."
            ),
        ),
        alias=MultilingualString(
            en="Log train every N steps", es="Registrar entrenamiento cada N pasos"
        ),
    )  # type: ignore

    log_validation_every_n_epochs: schema_field(
        none_type(int_field(ge=1)),
        placeholder=1,
        description=MultilingualString(
            en=(
                "Log metrics for validation split every n epochs during training. "
                "If None, it won't log per epoch."
            ),
            es=(
                "Registrar métricas del split de validación cada n épocas. "
                "Si es None, no registrará por época."
            ),
        ),
        alias=MultilingualString(
            en="Log validation every N epochs", es="Registrar validación cada N épocas"
        ),
    )  # type: ignore

    log_validation_every_n_steps: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Log metrics for validation split every n steps during training. "
                "If None, it won't log per step."
            ),
            es=(
                "Registrar métricas del split de validación cada n pasos. "
                "Si es None, no registrará por paso."
            ),
        ),
        alias=MultilingualString(
            en="Log validation every N steps", es="Registrar validación cada N pasos"
        ),
    )  # type: ignore


class MLP(nn.Module):
    def __init__(self, input_dim, hidden_size, activation_name):
        super().__init__()
        activations = {
            "relu": nn.ReLU(),
            "tanh": nn.Tanh(),
            "sigmoid": nn.Sigmoid(),
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
    DISPLAY_NAME: str = MultilingualString(
        en="Multi-layer Perceptron (MLP) Regression",
        es="Perceptrón Multicapa (MLP) Regresión",
    )
    DESCRIPTION: str = MultilingualString(
        en="Neural network with multiple hidden layers for regression.",
        es="Red neuronal con múltiples capas ocultas para regresión.",
    )
    COLOR: str = "#FF7043"
    ICON: str = "Psychology"

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
        batch_size = self.params.get("batch_size")
        if batch_size is None or batch_size > X_tensor.size(0):
            batch_size = X_tensor.size(0)

        global_step = 0
        for epoch in range(total_epochs):
            self.model.train()
            indices = torch.randperm(X_tensor.size(0))

            for i in range(0, X_tensor.size(0), batch_size):
                # Set model to train mode
                self.model.train()

                batch_idx = indices[i : i + batch_size]
                train_loss = criterion(
                    self.model(X_tensor[batch_idx]), y_tensor[batch_idx]
                )

                optimizer.zero_grad()
                train_loss.backward()
                optimizer.step()

                # Increment global step counter
                global_step += 1

                # Set model to eval for metric calculation
                self.model.eval()

                # Train metrics per step
                if self.log_train_every_n_steps and (
                    global_step % self.log_train_every_n_steps == 0
                ):
                    self.calculate_metrics(
                        split=SplitEnum.TRAIN,
                        level=LevelEnum.STEP,
                        x_data=x_train,
                        y_data=y_train,
                        log_index=global_step,
                    )

                # Validation metrics per step
                if (
                    self.log_validation_every_n_steps
                    and global_step % self.log_validation_every_n_steps == 0
                ):
                    self.calculate_metrics(
                        split=SplitEnum.VALIDATION,
                        level=LevelEnum.STEP,
                        x_data=x_validation,
                        y_data=y_validation,
                        log_index=global_step,
                    )

            # Set model to eval for metric calculation
            self.model.eval()

            # Train metrics per epoch
            if (
                self.log_train_every_n_epochs
                and (epoch + 1) % self.log_train_every_n_epochs == 0
            ):
                self.calculate_metrics(
                    split=SplitEnum.TRAIN,
                    level=LevelEnum.EPOCH,
                    x_data=x_train,
                    y_data=y_train,
                    log_index=epoch + 1,
                )

            # Validation metrics per epoch
            if (
                self.log_validation_every_n_epochs
                and (epoch + 1) % self.log_validation_every_n_epochs == 0
            ):
                self.calculate_metrics(
                    split=SplitEnum.VALIDATION,
                    level=LevelEnum.EPOCH,
                    x_data=x_validation,
                    y_data=y_validation,
                    log_index=epoch + 1,
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

"""DashAI CNN Model for time series classification."""

import os
from typing import Any, Dict, List, Optional

import datasets
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from beartype import beartype
from torch.utils.data import DataLoader
from torch.utils.data import Dataset as TorchDataset

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.models.base_model import BaseModel


class CNNModelSchema(BaseSchema):
    """Schema for CNN Model configuration parameters."""

    epochs: schema_field(
        int_field(ge=1),
        placeholder=10,
        description=(
            "The number of epochs to train the model. An epoch is a full "
            "iteration over the training data. Must be >= 1."
        ),
    )  # type: ignore

    learning_rate: schema_field(
        float_field(gt=0.0),
        placeholder=0.0003,
        description="Learning rate for model training. Must be > 0.",
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1),
        placeholder=32,
        description="Batch size for training. Must be >= 1.",
    )  # type: ignore

    hidden_dims: schema_field(
        list_field(int_field(ge=1), min_items=1),
        placeholder=[32, 64, 128],
        description=(
            "Number of filters for each convolutional layer. "
            "Specify comma-separated values (e.g., 32,64,128)."
        ),
    )  # type: ignore

    kernel_sizes: schema_field(
        list_field(int_field(ge=1), min_items=1),
        placeholder=[11, 7, 5],
        description=(
            "Kernel size for each convolutional layer. "
            "Must match the number of hidden_dims."
        ),
    )  # type: ignore

    pool_sizes: schema_field(
        list_field(int_field(ge=1), min_items=1),
        placeholder=[2, 2, 2],
        description=(
            "Pooling size for each convolutional layer. "
            "Must match the number of hidden_dims."
        ),
    )  # type: ignore

    dropout: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.1,
        description="Dropout rate for regularization (0.0 to 1.0).",
    )  # type: ignore

    optimizer: schema_field(
        enum_field(["Adam", "AdamW", "SGD"]),
        "AdamW",
        description="Optimizer to use for training.",
    )  # type: ignore

    weight_decay: schema_field(
        float_field(ge=0.0),
        placeholder=0.001,
        description="Weight decay (L2 regularization) for the optimizer.",
    )  # type: ignore


class ConvBlock(nn.Module):
    """Convolutional block with BatchNorm, ReLU, and optional pooling."""

    def __init__(self, in_ch, out_ch, k=7, s=1, p=None, pool=2, dropout=0.0):
        super().__init__()
        if p is None:
            p = k // 2  # same-ish padding
        self.conv = nn.Conv1d(
            in_ch, out_ch, kernel_size=k, stride=s, padding=p, bias=False
        )
        self.bn = nn.BatchNorm1d(out_ch)
        self.act = nn.ReLU(inplace=True)
        self.pool = nn.MaxPool1d(kernel_size=pool) if pool else nn.Identity()
        self.drop = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.act(x)
        x = self.pool(x)
        x = self.drop(x)
        return x


class TimeSeriesMetaCNN(nn.Module):
    """
    CNN for time series classification with metadata integration.

    Input:
      - x_ts: (B, 12, 5000) multivariate time series
      - x_meta: (B, metadata_dim) metadata features
    Output:
      - logits: (B, n_classes)
    """

    def __init__(
        self,
        metadata_dim: int = 2,
        n_classes: int = 6,
        ts_in_ch: int = 12,
        hidden_dims: List[int] = None,
        kernel_sizes: List[int] = None,
        pool_sizes: List[int] = None,
        dropout: float = 0.1,
    ):
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [32, 64, 128]
        if kernel_sizes is None:
            kernel_sizes = [11, 7, 5]
        if pool_sizes is None:
            pool_sizes = [2, 2, 2]

        # Validate parameters
        if not (len(hidden_dims) == len(kernel_sizes) == len(pool_sizes)):
            raise ValueError(
                "hidden_dims, kernel_sizes, and pool_sizes must have the same length"
            )

        # Build CNN layers
        layers = []
        in_channels = ts_in_ch
        for out_channels, k_size, p_size in zip(hidden_dims, kernel_sizes, pool_sizes):
            layers.append(
                ConvBlock(
                    in_channels, out_channels, k=k_size, pool=p_size, dropout=dropout
                )
            )
            in_channels = out_channels

        self.features = nn.Sequential(*layers)
        self.gap = nn.AdaptiveAvgPool1d(1)

        # Metadata MLP
        self.meta_mlp = nn.Sequential(
            nn.Linear(metadata_dim, 16, bias=True),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
        )

        # Classification head
        fused_dim = hidden_dims[-1] + 16
        self.head = nn.Sequential(
            nn.Linear(fused_dim, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 2),
            nn.Linear(128, n_classes),
        )

        # Initialize weights
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")

    def forward(self, x_ts, x_meta):
        # CNN path
        z = self.features(x_ts)
        z = self.gap(z).squeeze(-1)

        # Metadata path
        m = self.meta_mlp(x_meta)

        # Fuse and classify
        h = torch.cat([z, m], dim=1)
        logits = self.head(h)
        return logits


class ECGTorchDataset(TorchDataset):
    """Torch Dataset wrapper for ECG data from HuggingFace Dataset."""

    def __init__(
        self,
        hf_dataset: datasets.Dataset,
        metadata_cols: List[str],
        target_cols: List[str],
    ):
        self.dataset = hf_dataset
        self.metadata_cols = metadata_cols
        self.target_cols = target_cols

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        item = self.dataset[idx]

        # Time series: [12, 5000]
        time_series = torch.tensor(item["time_series"], dtype=torch.float32)

        # Metadata (handle missing values)
        metadata = []
        for col in self.metadata_cols:
            val = item.get(col, 0.0)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                val = 0.0
            metadata.append(float(val))
        metadata = torch.tensor(metadata, dtype=torch.float32)

        # Targets (binary multi-label -> convert to single class index)
        targets = []
        for col in self.target_cols:
            val = item.get(col, 0.0)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                val = 0.0
            targets.append(float(val))
        targets = torch.tensor(targets, dtype=torch.float32)

        # Convert multi-label to single class index
        # If any target is 1, use that index; otherwise use last index (normal)
        positive_indices = torch.where(targets > 0.5)[0]
        if len(positive_indices) > 0:
            target_idx = positive_indices[0].item()  # Extract scalar value
        else:
            target_idx = len(self.target_cols)  # "Normal" class

        # ✅ FIX: Return target_idx as a tensor instead of int
        target_idx_tensor = torch.tensor(target_idx, dtype=torch.long)

        return time_series, metadata, target_idx_tensor


class CNNModel(BaseModel):
    """CNN model for time series classification."""

    SCHEMA = CNNModelSchema
    COMPATIBLE_COMPONENTS = ["TimeSeriesClassificationTask"]

    def __init__(
        self,
        epochs: int = 10,
        learning_rate: float = 0.0003,
        batch_size: int = 32,
        hidden_dims: List[int] = None,
        kernel_sizes: List[int] = None,
        pool_sizes: List[int] = None,
        dropout: float = 0.1,
        optimizer: str = "AdamW",
        weight_decay: float = 0.001,
        **kwargs,
    ):
        """Initialize CNN model."""
        if hidden_dims is None:
            hidden_dims = [32, 64, 128]
        if kernel_sizes is None:
            kernel_sizes = [11, 7, 5]
        if pool_sizes is None:
            pool_sizes = [2, 2, 2]

        self.epochs = epochs
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.hidden_dims = hidden_dims
        self.kernel_sizes = kernel_sizes
        self.pool_sizes = pool_sizes
        self.dropout = dropout
        self.optimizer_name = optimizer
        self.weight_decay = weight_decay

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.metadata_cols = None
        self.target_cols = None
        self.n_classes = None

        # ✅ Store losses for each split
        self.train_loss = None
        self.val_loss = None
        self.test_loss = None

    @beartype
    def fit(self, x: datasets.Dataset, y: datasets.Dataset):
        """Train the CNN model.

        Parameters
        ----------
        x : datasets.Dataset
            Input dataset containing:
            - time_series: ECG signals (12 channels × 5000 samples)
            - metadata columns: age, sex, etc.
        y : datasets.Dataset
            Target dataset containing binary classification columns
        """
        # Merge x and y
        x_dict = x.to_dict()
        y_dict = y.to_dict()

        # Combine dictionaries
        combined_dict = {**x_dict, **y_dict}
        dataset = datasets.Dataset.from_dict(combined_dict)

        # Identify columns
        self.target_cols = list(y.column_names)
        all_cols = list(dataset.column_names)

        # Metadata columns are those not in targets and not special columns
        self.metadata_cols = [
            col
            for col in all_cols
            if col not in self.target_cols and col not in ["ecg_id", "time_series"]
        ]

        # Number of classes = targets + 1 normal class
        self.n_classes = len(self.target_cols) + 1

        print(f"Training configuration:")
        print(f"  - Metadata columns: {self.metadata_cols}")
        print(f"  - Target columns: {self.target_cols}")
        print(f"  - Number of classes: {self.n_classes}")
        print(f"  - Device: {self.device}")

        # Create torch dataset
        torch_dataset = ECGTorchDataset(dataset, self.metadata_cols, self.target_cols)
        train_loader = DataLoader(
            torch_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=True if self.device.type == "cuda" else False,
        )

        # Initialize model
        metadata_dim = len(self.metadata_cols) if self.metadata_cols else 1
        self.model = TimeSeriesMetaCNN(
            metadata_dim=metadata_dim,
            n_classes=self.n_classes,
            ts_in_ch=12,
            hidden_dims=self.hidden_dims,
            kernel_sizes=self.kernel_sizes,
            pool_sizes=self.pool_sizes,
            dropout=self.dropout,
        ).to(self.device)

        # Setup optimizer
        if self.optimizer_name == "Adam":
            optimizer = optim.Adam(
                self.model.parameters(),
                lr=self.learning_rate,
                weight_decay=self.weight_decay,
            )
        elif self.optimizer_name == "AdamW":
            optimizer = optim.AdamW(
                self.model.parameters(),
                lr=self.learning_rate,
                weight_decay=self.weight_decay,
            )
        else:  # SGD
            optimizer = optim.SGD(
                self.model.parameters(),
                lr=self.learning_rate,
                weight_decay=self.weight_decay,
                momentum=0.9,
            )

        criterion = nn.CrossEntropyLoss()

        # Training loop
        self.model.train()
        print("\nStarting training...")
        for epoch in range(self.epochs):
            running_loss = 0.0
            num_batches = 0

            for x_ts, x_meta, y_idx in train_loader:
                x_ts = x_ts.to(self.device)
                x_meta = x_meta.to(self.device)
                y_idx = y_idx.to(self.device)

                optimizer.zero_grad()
                logits = self.model(x_ts, x_meta)
                loss = criterion(logits, y_idx)
                loss.backward()
                optimizer.step()

                running_loss += loss.item()
                num_batches += 1

            avg_loss = running_loss / num_batches
            print(f"Epoch [{epoch+1}/{self.epochs}], Loss: {avg_loss:.4f}")

        # ✅ Store final training loss
        self.train_loss = avg_loss

    def evaluate_loss(self, x: datasets.Dataset, y: datasets.Dataset) -> float:
        """
        Evaluate the loss on a given dataset.

        Parameters
        ----------
        x : datasets.Dataset
            Input dataset
        y : datasets.Dataset
            Target dataset

        Returns
        -------
        float
            Average loss on the dataset
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call fit() first.")

        # Merge x and y
        x_dict = x.to_dict()
        y_dict = y.to_dict()
        combined_dict = {**x_dict, **y_dict}
        dataset = datasets.Dataset.from_dict(combined_dict)

        torch_dataset = ECGTorchDataset(dataset, self.metadata_cols, self.target_cols)
        loader = DataLoader(
            torch_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=True if self.device.type == "cuda" else False,
        )

        criterion = nn.CrossEntropyLoss()
        self.model.eval()

        running_loss = 0.0
        num_batches = 0

        with torch.no_grad():
            for x_ts, x_meta, y_idx in loader:
                x_ts = x_ts.to(self.device)
                x_meta = x_meta.to(self.device)
                y_idx = y_idx.to(self.device)

                logits = self.model(x_ts, x_meta)
                loss = criterion(logits, y_idx)

                running_loss += loss.item()
                num_batches += 1

        return running_loss / num_batches if num_batches > 0 else 0.0

    @beartype
    def predict(self, x: datasets.Dataset) -> np.ndarray:
        """Make predictions on input data.

        Parameters
        ----------
        x : datasets.Dataset
            Input dataset containing time_series and metadata columns

        Returns
        -------
        np.ndarray
            Probability distributions over classes, shape (n_samples, n_classes)
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call fit() first.")

        # Create dummy targets for compatibility with ECGTorchDataset
        dummy_targets = {col: [0.0] * len(x) for col in self.target_cols}

        x_dict = x.to_dict()
        combined_dict = {**x_dict, **dummy_targets}
        dataset = datasets.Dataset.from_dict(combined_dict)

        torch_dataset = ECGTorchDataset(dataset, self.metadata_cols, self.target_cols)
        test_loader = DataLoader(
            torch_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=True if self.device.type == "cuda" else False,
        )

        self.model.eval()
        all_probs = []

        with torch.no_grad():
            for x_ts, x_meta, _ in test_loader:
                x_ts = x_ts.to(self.device)
                x_meta = x_meta.to(self.device)

                logits = self.model(x_ts, x_meta)
                probs = torch.softmax(logits, dim=1)
                all_probs.append(probs.cpu().numpy())

        # Concatenate all batches
        all_probs = np.vstack(all_probs)
        return all_probs

    def save(self, filename: str) -> None:
        """Save model checkpoint."""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")

        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "hidden_dims": self.hidden_dims,
            "kernel_sizes": self.kernel_sizes,
            "pool_sizes": self.pool_sizes,
            "dropout": self.dropout,
            "optimizer_name": self.optimizer_name,
            "weight_decay": self.weight_decay,
            "metadata_cols": self.metadata_cols,
            "target_cols": self.target_cols,
            "n_classes": self.n_classes,
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "test_loss": self.test_loss,
        }
        torch.save(checkpoint, filename)
        print(f"Model saved to {filename}")

    @classmethod
    def load(cls, filename: str) -> "CNNModel":
        """Load model from checkpoint."""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Checkpoint file not found: {filename}")

        checkpoint = torch.load(filename, map_location=torch.device("cpu"))

        instance = cls(
            epochs=checkpoint["epochs"],
            learning_rate=checkpoint["learning_rate"],
            batch_size=checkpoint["batch_size"],
            hidden_dims=checkpoint["hidden_dims"],
            kernel_sizes=checkpoint["kernel_sizes"],
            pool_sizes=checkpoint["pool_sizes"],
            dropout=checkpoint["dropout"],
            optimizer=checkpoint["optimizer_name"],
            weight_decay=checkpoint["weight_decay"],
        )

        instance.metadata_cols = checkpoint["metadata_cols"]
        instance.target_cols = checkpoint["target_cols"]
        instance.n_classes = checkpoint["n_classes"]
        instance.train_loss = checkpoint.get("train_loss")
        instance.val_loss = checkpoint.get("val_loss")
        instance.test_loss = checkpoint.get("test_loss")

        # Recreate model
        metadata_dim = len(instance.metadata_cols) if instance.metadata_cols else 1
        instance.model = TimeSeriesMetaCNN(
            metadata_dim=metadata_dim,
            n_classes=instance.n_classes,
            ts_in_ch=12,
            hidden_dims=instance.hidden_dims,
            kernel_sizes=instance.kernel_sizes,
            pool_sizes=instance.pool_sizes,
            dropout=instance.dropout,
        )
        instance.model.load_state_dict(checkpoint["model_state_dict"])
        instance.model.to(instance.device)

        print(f"Model loaded from {filename}")
        return instance

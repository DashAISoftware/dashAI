"""Shared classes for Hugging Face text classification transformers."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from sklearn.exceptions import NotFittedError

from DashAI.back.models.text_classification_model import TextClassificationModel
from DashAI.back.models.utils import GPU_OR_CPU_PLACEHOLDER
from DashAI.back.types.categorical import Categorical

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class HuggingFaceTextClassificationTransformer(TextClassificationModel):
    """Base implementation for Hugging Face text classification wrappers."""

    MODEL_NAME: str = ""
    TEMP_CHECKPOINT_DIR: str = (
        "DashAI/back/user_models/temp_checkpoints_hf_text_classification"
    )
    MAX_TOKEN_LENGTH: int = 512

    def __init__(self, model=None, **kwargs):
        """Initialize tokenizer, model and training configuration."""

        self.num_labels = kwargs.pop("num_labels", None)
        kwargs.pop("model_name", None)

        kwargs = self.validate_and_transform(kwargs)

        from transformers import AutoTokenizer

        if not self.MODEL_NAME:
            raise ValueError(
                f"{self.__class__.__name__} must define a non-empty MODEL_NAME."
            )

        self.model_name = self.MODEL_NAME
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        self.log_train_every_n_epochs = kwargs.get("log_train_every_n_epochs", 1)
        self.log_train_every_n_steps = kwargs.get("log_train_every_n_steps", None)
        self.log_validation_every_n_epochs = kwargs.get(
            "log_validation_every_n_epochs", 1
        )
        self.log_validation_every_n_steps = kwargs.get(
            "log_validation_every_n_steps", None
        )

        self.training_args_params = {
            "num_train_epochs": kwargs.get("num_train_epochs", 2),
            "learning_rate": kwargs.get("learning_rate", 5e-5),
            "weight_decay": kwargs.get("weight_decay", 0.01),
        }
        self.batch_size = kwargs.get("batch_size", 16)
        self.device = kwargs.get("device") or GPU_OR_CPU_PLACEHOLDER

        if model is not None:
            self.model = model
            if self.num_labels is not None and hasattr(self.model, "config"):
                self.model.config.num_labels = self.num_labels
                if self.num_labels > 1:
                    self.model.config.problem_type = "single_label_classification"
        else:
            from transformers import AutoConfig, AutoModelForSequenceClassification

            model_config = AutoConfig.from_pretrained(self.model_name)
            if self.num_labels is not None:
                model_config.num_labels = self.num_labels
                if self.num_labels > 1:
                    model_config.problem_type = "single_label_classification"
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name, config=model_config
            )

        self.fitted = False
        self.encodings = {}  # Store encodings for categorical columns

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        import shutil
        import tempfile
        from pathlib import Path

        import torch
        from transformers import (
            AutoConfig,
            AutoModelForSequenceClassification,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )

        from DashAI.back.models.hugging_face.metrics_callback import MetricsCallback

        output_column_name = y_train.column_names[0]

        if self.num_labels is None:
            self.num_labels = len(y_train.unique(output_column_name))
            config = AutoConfig.from_pretrained(
                self.model_name, num_labels=self.num_labels
            )
            if self.num_labels > 1:
                config.problem_type = "single_label_classification"
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name, config=config
            )

        x_train_prepared = self.prepare_dataset(x_train, is_fit=True)
        y_train_prepared = self.prepare_dataset(y_train, is_fit=True)
        train_dataset = x_train_prepared.add_column(
            "label", y_train_prepared[output_column_name]
        )

        has_validation_data = x_validation is not None and y_validation is not None
        validation_dataset = None
        if has_validation_data:
            x_validation_prepared = self.prepare_dataset(x_validation)
            y_validation_prepared = self.prepare_dataset(y_validation)
            validation_dataset = x_validation_prepared.add_column(
                "label", y_validation_prepared[output_column_name]
            )

        num_epochs = self.training_args_params.get("num_train_epochs", 2)
        use_gpu = self.device.lower() == "gpu"
        can_use_fp16 = torch.cuda.is_available() and use_gpu

        base_output_dir = Path(self.TEMP_CHECKPOINT_DIR)
        base_output_dir.mkdir(parents=True, exist_ok=True)
        run_output_dir = tempfile.mkdtemp(
            prefix=f"{self.__class__.__name__.lower()}_",
            dir=str(base_output_dir),
        )

        training_args_obj = TrainingArguments(
            output_dir=run_output_dir,
            save_strategy="epoch",
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            eval_strategy="no",
            use_cpu=not use_gpu,
            fp16=can_use_fp16,
            **self.training_args_params,
        )

        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)

        metrics_callback = MetricsCallback(
            model_instance=self,
            x_train=x_train,
            y_train=y_train,
            x_val=x_validation,
            y_val=y_validation,
            total_epochs=num_epochs,
            log_training_every_n_epochs=self.log_train_every_n_epochs,
            log_training_every_n_steps=self.log_train_every_n_steps,
            log_val_every_n_epochs=(
                self.log_validation_every_n_epochs if has_validation_data else None
            ),
            log_val_every_n_steps=(
                self.log_validation_every_n_steps if has_validation_data else None
            ),
        )

        trainer = Trainer(
            model=self.model,
            args=training_args_obj,
            train_dataset=train_dataset,
            eval_dataset=validation_dataset,
            data_collator=data_collator,
            callbacks=[metrics_callback],
        )

        self.fitted = True
        try:
            trainer.train()
        finally:
            shutil.rmtree(run_output_dir, ignore_errors=True)

        return self

    def predict(self, x_pred: "DashAIDataset"):
        """Predict class probabilities for text examples."""

        if not self.fitted:
            raise NotFittedError(
                f"This {self.__class__.__name__} instance is not fitted yet. Call 'fit'"
                " with appropriate arguments before using this estimator."
            )

        pred_dataset = self.prepare_dataset(x_pred)

        import numpy as np
        from torch.utils.data import DataLoader
        from transformers import DataCollatorWithPadding

        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        text_columns = [col for col in x_pred.column_names if col != "label"]
        if len(text_columns) != 1:
            raise ValueError(f"Expected exactly one text column, found: {text_columns}")

        pred_loader = DataLoader(
            pred_dataset.remove_columns(text_columns[0]),
            batch_size=self.batch_size,
            collate_fn=data_collator,
        )

        probabilities = []

        for batch in pred_loader:
            inputs = {
                k: v.to(self.model.device) for k, v in batch.items() if k != "labels"
            }

            outputs = self.model(**inputs)
            probs = outputs.logits.softmax(dim=-1)
            probabilities.append(probs.detach().cpu().numpy())

        return np.vstack(probabilities)

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Apply label encoding for categorical data or tokenize text."""
        from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
            apply_categorical_label_encoder,
            categorical_label_encoder,
        )

        has_categorical = any(
            isinstance(col_type, Categorical) for col_type in dataset.types.values()
        )

        if has_categorical:
            if is_fit:
                dataset, encodings = categorical_label_encoder(dataset)
                self.encodings.update(encodings)
            else:
                dataset = apply_categorical_label_encoder(dataset, self.encodings)
            return dataset

        return self.tokenize_data(dataset)

    def tokenize_data(self, dataset: "DashAIDataset") -> "DashAIDataset":
        """Tokenize the text input column."""
        text_columns = [
            col
            for col in dataset.column_names
            if not isinstance(dataset.types.get(col), Categorical)
        ]
        if len(text_columns) != 1:
            raise ValueError(f"Expected exactly one text column, found: {text_columns}")

        return dataset.map(
            lambda batch: self.tokenizer(
                batch[text_columns[0]],
                truncation=True,
                padding=True,
                max_length=self.MAX_TOKEN_LENGTH,
            ),
            batched=True,
        )

    def save(self, filename: Union[str, "Path"]) -> None:
        """Persist transformer weights and custom training params."""
        from transformers import AutoConfig

        save_dir = Path(filename)
        if save_dir.exists() and save_dir.is_file():
            save_dir.unlink()
        save_dir.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(save_dir)
        config = AutoConfig.from_pretrained(save_dir)
        config.custom_params = {
            "num_train_epochs": self.training_args_params.get("num_train_epochs"),
            "batch_size": self.batch_size,
            "learning_rate": self.training_args_params.get("learning_rate"),
            "device": self.device,
            "weight_decay": self.training_args_params.get("weight_decay"),
            "num_labels": self.num_labels,
            "fitted": self.fitted,
        }
        config.save_pretrained(save_dir)

    @classmethod
    def load(cls, filename: Union[str, "Path"]) -> Any:
        """Restore transformer instance from a saved directory."""
        from transformers import AutoConfig, AutoModelForSequenceClassification

        config = AutoConfig.from_pretrained(filename)
        custom_params = getattr(config, "custom_params", {})

        model = AutoModelForSequenceClassification.from_pretrained(
            filename, num_labels=custom_params.get("num_labels")
        )

        loaded_model = cls(
            model=model,
            num_labels=custom_params.get("num_labels"),
            num_train_epochs=custom_params.get("num_train_epochs", 2),
            batch_size=custom_params.get("batch_size", 16),
            learning_rate=custom_params.get("learning_rate", 5e-5),
            device=custom_params.get("device", GPU_OR_CPU_PLACEHOLDER),
            weight_decay=custom_params.get("weight_decay", 0.01),
            log_train_every_n_epochs=None,
            log_train_every_n_steps=None,
            log_validation_every_n_epochs=None,
            log_validation_every_n_steps=None,
        )
        loaded_model.fitted = custom_params.get("fitted", False)
        return loaded_model

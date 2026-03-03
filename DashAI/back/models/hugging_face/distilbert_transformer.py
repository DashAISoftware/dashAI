"""DashAI implementation of DistilBERT model for english classification."""

from pathlib import Path
from typing import Any, Union

import torch
from sklearn.exceptions import NotFittedError
from torch.utils.data import DataLoader
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
    apply_categorical_label_encoder,
    categorical_label_encoder,
)
from DashAI.back.models.hugging_face.metrics_callback import MetricsCallback
from DashAI.back.models.text_classification_model import TextClassificationModel
from DashAI.back.types.categorical import Categorical


class DistilBertTransformerSchema(BaseSchema):
    """Distilbert is a transformer that allows you to classify text in English.
    The implementation is based on huggingface distilbert-base in the case of
    the uncased model, i.e. distilbert-base-uncased.
    """

    num_train_epochs: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en="Total number of training epochs to perform.",
            es="Número total de épocas de entrenamiento a realizar.",
        ),
        alias=MultilingualString(en="Num train epochs", es="Número de épocas"),
    )  # type: ignore
    batch_size: schema_field(
        int_field(ge=1),
        placeholder=16,
        description=MultilingualString(
            en="The batch size per GPU/TPU core/CPU for training",
            es="El tamaño de lote por núcleo GPU/TPU/CPU para entrenamiento",
        ),
        alias=MultilingualString(en="Batch size", es="Tamaño de lote"),
    )  # type: ignore
    learning_rate: schema_field(
        float_field(ge=0.0),
        placeholder=3e-5,
        description=MultilingualString(
            en="The initial learning rate for AdamW optimizer",
            es="La tasa de aprendizaje inicial para el optimizador AdamW",
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
    )  # type: ignore
    device: schema_field(
        enum_field(enum=["gpu", "cpu"]),
        placeholder="gpu",
        description=MultilingualString(
            en=(
                "Hardware on which the training is run. If available, GPU is "
                "recommended for efficiency reasons. Otherwise, use CPU."
            ),
            es=(
                "Hardware en el que se ejecuta el entrenamiento. Si está disponible, "
                "se recomienda GPU por razones de eficiencia. De lo contrario, use CPU."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore
    weight_decay: schema_field(
        float_field(ge=0.0),
        placeholder=0.01,
        description=MultilingualString(
            en=(
                "Weight decay is a regularization technique used in training "
                "neural networks to prevent overfitting. In the context of the AdamW "
                "optimizer, the 'weight_decay' parameter is the rate at which the "
                "weights of all layers are reduced during training, provided that "
                "this rate is not zero."
            ),
            es=(
                "Weight decay es una técnica de regularización usada en el "
                "entrenamiento de redes neuronales para prevenir sobreajuste. En el "
                "contexto del optimizador AdamW, el parámetro 'weight_decay' es la "
                "tasa a la cual los pesos de todas las capas se reducen durante el "
                "entrenamiento, siempre que esta tasa no sea cero."
            ),
        ),
        alias=MultilingualString(en="Weight decay", es="Decaimiento de pesos"),
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


class DistilBertTransformer(TextClassificationModel):
    """Pre-trained transformer DistilBERT allowing English text classification.

    DistilBERT is a small, fast, cheap and light Transformer model trained by
    distilling BERT base.
    It has 40% less parameters than bert-base-uncased, runs 60% faster while preserving
    over 95% of BERT's performances as measured on the GLUE language understanding
    benchmark [1].

    References
    ----------
    [1] https://huggingface.co/docs/transformers/model_doc/distilbert
    """

    DISPLAY_NAME: str = MultilingualString(
        en="DistilBERT Transformer",
        es="Transformer DistilBERT",
    )
    DESCRIPTION: str = MultilingualString(
        en="Distilled BERT model for efficient text classification.",
        es="Modelo BERT destilado para clasificación de texto eficiente.",
    )
    COLOR: str = "#96008E"
    ICON: str = "Psychology"
    SCHEMA = DistilBertTransformerSchema

    def __init__(self, model=None, **kwargs):
        """Initialize the transformer model.

        The process includes the instantiation of the pre-trained model and the
        associated tokenizer.
        """

        self.num_labels = kwargs.pop("num_labels", None)

        kwargs = self.validate_and_transform(kwargs)

        self.model_name = "distilbert-base-uncased"

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
        self.device = kwargs.get("device", "gpu")

        if model is not None:
            self.model = model
            if self.num_labels is not None and hasattr(self.model, "config"):
                self.model.config.num_labels = self.num_labels
                if self.num_labels > 1:
                    self.model.config.problem_type = "single_label_classification"
        else:
            model_config = AutoConfig.from_pretrained(self.model_name)
            if self.num_labels is not None:
                model_config.num_labels = self.num_labels
                if self.num_labels > 1:
                    model_config.problem_type = "single_label_classification"
            # Fallback: num_labels will be determined in fit().
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name, config=model_config
            )

        self.fitted = False
        self.encodings = {}  # Store encodings for categorical columns

    def train(self, x_train, y_train, x_validation, y_validation):
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

        # Train dataset preparation
        x_train_prepared = self.prepare_dataset(x_train, is_fit=True)
        y_train_prepared = self.prepare_dataset(y_train, is_fit=True)
        train_dataset = x_train_prepared.add_column(
            "label", y_train_prepared[output_column_name]
        )

        # Validation dataset preparation
        x_validation_prepared = self.prepare_dataset(x_validation)
        y_validation_prepared = self.prepare_dataset(y_validation)
        validation_dataset = x_validation_prepared.add_column(
            "label", y_validation_prepared[output_column_name]
        )

        # Get number of epochs from training args
        num_epochs = self.training_args_params.get("num_train_epochs", 2)

        can_use_fp16 = torch.cuda.is_available() and self.device == "gpu"
        training_args_obj = TrainingArguments(
            output_dir=None,
            save_strategy="epoch",
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            eval_strategy="no",
            use_cpu=self.device != "gpu",
            fp16=can_use_fp16,
            **self.training_args_params,
        )

        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)

        # Initialize the custom callback with epoch information
        metrics_callback = MetricsCallback(
            model_instance=self,
            x_train=x_train,
            y_train=y_train,
            x_val=x_validation,
            y_val=y_validation,
            total_epochs=num_epochs,
            log_training_every_n_epochs=self.log_train_every_n_epochs,
            log_training_every_n_steps=self.log_train_every_n_steps,
            log_val_every_n_epochs=self.log_validation_every_n_epochs,
            log_val_every_n_steps=self.log_validation_every_n_steps,
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
        trainer.train()
        return self

    def predict(self, x_pred: DashAIDataset):
        """Predict with the fine-tuned model.

        Parameters
        ----------
        x_pred : DashAIDataset
            Dataset with text data.

        Returns
        -------
        List
            List of predicted probabilities for each class.
        """

        if not self.fitted:
            raise NotFittedError(
                f"This {self.__class__.__name__} instance is not fitted yet. Call 'fit'"
                " with appropriate arguments before using this estimator."
            )

        pred_dataset = self.prepare_dataset(x_pred)

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
            probabilities.extend(probs.detach().cpu().numpy())

        return probabilities

    def prepare_dataset(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Apply the model transformations to the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool
            Whether this is for fitting (True) or prediction (False).

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
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
        else:
            return self.tokenize_data(dataset)

    def tokenize_data(self, dataset: DashAIDataset) -> DashAIDataset:
        """Tokenize the input data.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset with the input data to preprocess.

        Returns
        -------
        DashAIDataset
            Dataset with the tokenized input data.
        """
        text_columns = [
            col
            for col in dataset.column_names
            if not isinstance(dataset.types.get(col), Categorical)
        ]
        if len(text_columns) != 1:
            raise ValueError(f"Expected exactly one text column, found: {text_columns}")

        return dataset.map(
            lambda batch: self.tokenizer(
                batch[text_columns[0]], truncation=True, padding=True, max_length=512
            ),
            batched=True,
        )

    def save(self, filename: Union[str, Path]) -> None:
        self.model.save_pretrained(filename)
        config = AutoConfig.from_pretrained(filename)
        config.custom_params = {
            "num_train_epochs": self.training_args_params.get("num_train_epochs"),
            "batch_size": self.batch_size,
            "learning_rate": self.training_args_params.get("learning_rate"),
            "device": self.device,
            "weight_decay": self.training_args_params.get("weight_decay"),
            "num_labels": self.num_labels,
            "fitted": self.fitted,
            "log_train_every_n_epochs": self.log_train_every_n_epochs,
            "log_train_every_n_steps": self.log_train_every_n_steps,
            "log_validation_every_n_epochs": self.log_validation_every_n_epochs,
            "log_validation_every_n_steps": self.log_validation_every_n_steps,
        }

        config.save_pretrained(filename)

    @classmethod
    def load(cls, filename: Union[str, Path]) -> Any:
        config = AutoConfig.from_pretrained(filename)
        custom_params = getattr(config, "custom_params", {})

        model = AutoModelForSequenceClassification.from_pretrained(
            filename, num_labels=custom_params.get("num_labels")
        )
        loaded_model = cls(
            model=model,
            model_name=config.model_type,
            num_labels=custom_params.get("num_labels"),
            num_train_epochs=custom_params.get("num_train_epochs"),
            batch_size=custom_params.get("batch_size"),
            learning_rate=custom_params.get("learning_rate"),
            device=custom_params.get("device"),
            weight_decay=custom_params.get("weight_decay"),
            log_train_every_n_epochs=custom_params.get("log_train_every_n_epochs"),
            log_train_every_n_steps=custom_params.get("log_train_every_n_steps"),
            log_validation_every_n_epochs=custom_params.get(
                "log_validation_every_n_epochs"
            ),
            log_validation_every_n_steps=custom_params.get(
                "log_validation_every_n_steps"
            ),
        )
        loaded_model.fitted = custom_params.get("fitted")

        return loaded_model

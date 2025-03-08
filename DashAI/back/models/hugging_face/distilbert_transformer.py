"""DashAI implementation of DistilBERT model for english classification."""

import shutil
from pathlib import Path
from typing import Any, Union

import torch
from datasets import Dataset
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
    schema_field,
)
from DashAI.back.models.text_classification_model import TextClassificationModel


class DistilBertTransformerSchema(BaseSchema):
    """Distilbert is a transformer that allows you to classify text in English.
    The implementation is based on huggingface distilbert-base in the case of
    the uncased model, i.e. distilbert-base-uncased.
    """

    num_train_epochs: schema_field(
        int_field(ge=1),
        placeholder=2,
        description="Total number of training epochs to perform.",
    )  # type: ignore
    batch_size: schema_field(
        int_field(ge=1),
        placeholder=16,
        description="The batch size per GPU/TPU core/CPU for training",
    )  # type: ignore
    learning_rate: schema_field(
        float_field(ge=0.0),
        placeholder=5e-5,
        description="The initial learning rate for AdamW optimizer",
    )  # type: ignore
    device: schema_field(
        enum_field(enum=["gpu", "cpu"]),
        placeholder="gpu",
        description="Hardware on which the training is run. If available, GPU is "
        "recommended for efficiency reasons. Otherwise, use CPU.",
    )  # type: ignore
    weight_decay: schema_field(
        float_field(ge=0.0),
        placeholder=0.01,
        description="Weight decay is a regularization technique used in training "
        "neural networks to prevent overfitting. In the context of the AdamW "
        "optimizer, the 'weight_decay' parameter is the rate at which the weights of "
        "all layers are reduced during training, provided that this rate is not zero.",
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

    SCHEMA = DistilBertTransformerSchema

    def __init__(self, model=None, **kwargs):
        """Initialize the transformer model.

        The process includes the instantiation of the pre-trained model and the
        associated tokenizer.
        """
        self.num_labels = kwargs.get("num_labels")
        kwargs = self.validate_and_transform(kwargs)
        self.model_name = "distilbert-base-uncased"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.training_args = {
            "num_train_epochs": kwargs.get("num_train_epochs", 2),
            "learning_rate": kwargs.get("learning_rate", 5e-5),
            "weight_decay": kwargs.get("weight_decay", 0.01),
        }
        self.batch_size = kwargs.get("batch_size", 16)
        self.device = kwargs.get("device", "gpu")
        self.model = (
            model
            if model is not None
            else AutoModelForSequenceClassification.from_pretrained(self.model_name)
        )

        self.fitted = False

    def tokenize_data(self, dataset: Dataset) -> Dataset:
        """Tokenize the input data.

        Parameters
        ----------
        dataset : Dataset
            Dataset with the input data to preprocess.

        Returns
        -------
        Dataset
            Dataset with the tokenized input data.
        """
        return dataset.map(
            lambda examples: self.tokenizer(
                examples["text"], truncation=True, padding=True, max_length=512
            ),
            batched=True,
        )

    def fit(self, x_train: Dataset, y_train: Dataset):
        """Fine-tune the pre-trained model.

        Parameters
        ----------
        x_train : Dataset
            Dataset with input training data.
        y_train : Dataset
            Dataset with output training data.

        """
        output_column_name = y_train.column_names[0]
        if self.num_labels is None:
            self.num_labels = len(set(y_train[output_column_name]))
        self.model.config.num_labels = self.num_labels
        train_dataset = self.tokenize_data(x_train)
        train_dataset = train_dataset.add_column("label", y_train[output_column_name])

        can_use_fp16 = torch.cuda.is_available() and self.device == "gpu"
        training_args = TrainingArguments(
            output_dir="DashAI/back/user_models/temp_checkpoints_distilbert",
            logging_strategy="steps",
            logging_steps=50,
            save_strategy="epoch",  # Guarda checkpoints al final de cada época
            per_device_train_batch_size=self.batch_size,
            no_cuda=self.device != "gpu",
            fp16=can_use_fp16,
            **self.training_args,
        )

        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
        )

        trainer.train()
        self.fitted = True
        shutil.rmtree(
            "DashAI/back/user_models/temp_checkpoints_distilbert", ignore_errors=True
        )
        return self

    def predict(self, x_pred: Dataset):
        """Predict with the fine-tuned model.

        Parameters
        ----------
        x_pred : Dataset
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

        pred_dataset = self.tokenize_data(x_pred)

        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        pred_loader = DataLoader(
            pred_dataset.remove_columns(["text"]),
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

    def save(self, filename: Union[str, Path]) -> None:
        self.model.save_pretrained(filename)
        config = AutoConfig.from_pretrained(filename)
        config.custom_params = {
            "num_train_epochs": self.training_args.get("num_train_epochs"),
            "batch_size": self.batch_size,
            "learning_rate": self.training_args.get("learning_rate"),
            "device": self.device,
            "weight_decay": self.training_args.get("weight_decay"),
            "num_labels": self.num_labels,
            "fitted": self.fitted,
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
        )
        loaded_model.fitted = custom_params.get("fitted")

        return loaded_model

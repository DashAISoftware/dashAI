"""OpusMtEsENTransformer model for spanish-english translation DashAI implementation."""

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from sklearn.exceptions import NotFittedError

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)
from DashAI.back.models.translation_model import TranslationModel
from DashAI.back.models.utils import GPU_OR_CPU_PLACEHOLDER

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class OpusMtEsENTransformerSchema(OpusMtEnESTransformerSchema):
    """opus-mt-es-en is a transformer pre-trained model that allows translation of
    texts from Spanish to English. The implementation is based on the Helsinki-NLP
    opus-mt-es-en checkpoint, which uses the MarianMT architecture and was trained
    on parallel corpora from the OPUS collection.
    """


class OpusMtEsENTransformer(TranslationModel):
    """Pre-trained transformer for Spanish-to-English translation.

    This model fine-tunes the Helsinki-NLP ``opus-mt-es-en`` checkpoint, which is
    based on the MarianMT sequence-to-sequence architecture. The base model was
    trained on parallel Spanish-English corpora from the OPUS collection and supports
    direct translation without intermediate pivot languages.

    Fine-tuning is performed with the HuggingFace ``Seq2SeqTrainer`` using the AdamW
    optimizer. Training and validation metrics are logged at configurable epoch and
    step intervals via a custom ``MetricsCallback``.

    References
    ----------
    - [1] https://huggingface.co/Helsinki-NLP/opus-mt-es-en
    - [2] https://opus.nlpl.eu/
    """

    SCHEMA = OpusMtEsENTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT Es-En Transformer",
        es="Transformer Opus MT Es-En",
    )
    DESCRIPTION: str = MultilingualString(
        en="Pre-trained transformer for Spanish-English translation.",
        es="Transformer pre-entrenado para traducción español-inglés.",
    )
    COLOR: str = "#FF8A65"
    ICON: str = "Translate"

    def __init__(self, model=None, **kwargs):
        """Initialize the transformer.

        Downloads the ``Helsinki-NLP/opus-mt-es-en`` tokenizer and, when
        ``model`` is ``None``, the seq2seq model weights from HuggingFace.
        When a pre-loaded model is supplied, the weights are reused directly
        and ``fitted`` is set to ``True``.

        Parameters
        ----------
        model : transformers.PreTrainedModel or None, optional
            An already-loaded HuggingFace seq2seq model to reuse. If ``None``,
            the ``Helsinki-NLP/opus-mt-es-en`` checkpoint is downloaded and
            initialised. Default ``None``.
        **kwargs : dict
            Hyperparameters forwarded to ``validate_and_transform`` and used to
            configure training (e.g. ``num_train_epochs``, ``batch_size``,
            ``learning_rate``, ``weight_decay``, ``device``).
        """
        kwargs = self.validate_and_transform(kwargs)

        from transformers import AutoTokenizer

        self.model_name = "Helsinki-NLP/opus-mt-es-en"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        self.training_args = {
            "num_train_epochs": kwargs.get("num_train_epochs", 2),
            "learning_rate": kwargs.get("learning_rate", 2e-5),
            "weight_decay": kwargs.get("weight_decay", 0.01),
        }
        self.batch_size = kwargs.get("batch_size", 4)
        self.device = kwargs.get("device") or GPU_OR_CPU_PLACEHOLDER
        self.log_train_every_n_epochs = kwargs.get("log_train_every_n_epochs", 1)
        self.log_train_every_n_steps = kwargs.get("log_train_every_n_steps", None)
        self.log_validation_every_n_epochs = kwargs.get(
            "log_validation_every_n_epochs", 1
        )
        self.log_validation_every_n_steps = kwargs.get(
            "log_validation_every_n_steps", None
        )

        if model is None:
            from transformers import AutoModelForSeq2SeqLM

            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        else:
            self.model = model

        self.num_train_epochs = self.training_args.get("num_train_epochs", 2)
        self.fitted = model is not None

    def tokenize_data(
        self, x: "DashAIDataset", y: Optional["DashAIDataset"] = None
    ) -> "DashAIDataset":
        """Tokenize input and optional target datasets for seq2seq training.

        Each sample is tokenized with truncation and max-length padding to 512
        tokens. When ``y`` is provided, the target tokens are stored under the
        ``labels`` key so the ``Seq2SeqTrainer`` can compute the loss directly.

        Parameters
        ----------
        x : DashAIDataset
            Source-language dataset. Only the first column is used.
        y : DashAIDataset, optional
            Target-language dataset. When provided, tokenized targets are added
            as ``labels``. When ``None``, only ``input_ids`` and
            ``attention_mask`` are returned (inference mode).

        Returns
        -------
        DashAIDataset
            Tokenized dataset with keys ``input_ids``, ``attention_mask``, and
            optionally ``labels``.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        is_y = bool(y)
        if not y:
            y = DashAIDataset.from_list([{"foo": 0}] * len(x))

        dataset = []
        input_column_name = x.column_names[0]
        output_column_name = y.column_names[0] if is_y else None

        for i, input_sample in enumerate(x):
            tokenized_input = self.tokenizer(
                input_sample[input_column_name],
                truncation=True,
                padding="max_length",
                max_length=512,
            )

            sample = {
                "input_ids": tokenized_input["input_ids"],
                "attention_mask": tokenized_input["attention_mask"],
            }

            if is_y:
                output_sample = y[i]
                tokenized_output = self.tokenizer(
                    output_sample[output_column_name],
                    truncation=True,
                    padding="max_length",
                    max_length=512,
                )
                sample["labels"] = tokenized_output["input_ids"]

            dataset.append(sample)

        return DashAIDataset.from_list(dataset)

    def train(
        self,
        x_train: "DashAIDataset",
        y_train: "DashAIDataset",
        x_validation: "DashAIDataset" = None,
        y_validation: "DashAIDataset" = None,
    ) -> "OpusMtEsENTransformer":
        """Fine-tune the opus-mt-es-en model on Spanish-English translation data.

        Parameters
        ----------
        x_train : DashAIDataset
            Input Spanish text features for training.
        y_train : DashAIDataset
            Target English translation labels for training.
        x_validation : DashAIDataset, optional
            Input Spanish text features for validation. Default ``None``.
        y_validation : DashAIDataset, optional
            Target English translation labels for validation. Default ``None``.

        Returns
        -------
        OpusMtEsENTransformer
            The fine-tuned model instance.
        """
        from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

        from DashAI.back.models.hugging_face.metrics_callback import MetricsCallback

        dataset = self.tokenize_data(x_train, y_train)
        dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

        has_validation_data = x_validation is not None and y_validation is not None

        output_root = Path("DashAI/back/user_models/temp_checkpoints_opus-mt-es-en")
        output_root.mkdir(parents=True, exist_ok=True)
        run_output_dir = tempfile.mkdtemp(prefix="opus_mt_es_en_", dir=str(output_root))

        training_args = Seq2SeqTrainingArguments(
            output_dir=run_output_dir,
            save_steps=1,
            save_total_limit=1,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            use_cpu=self.device.lower() != "gpu",
            **self.training_args,
        )

        metrics_callback = MetricsCallback(
            model_instance=self,
            x_train=x_train,
            y_train=y_train,
            x_val=x_validation,
            y_val=y_validation,
            total_epochs=self.num_train_epochs,
            log_training_every_n_epochs=self.log_train_every_n_epochs,
            log_training_every_n_steps=self.log_train_every_n_steps,
            log_val_every_n_epochs=(
                self.log_validation_every_n_epochs if has_validation_data else None
            ),
            log_val_every_n_steps=(
                self.log_validation_every_n_steps if has_validation_data else None
            ),
        )

        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            callbacks=[metrics_callback],
        )

        self.fitted = True
        try:
            trainer.train()
        finally:
            shutil.rmtree(run_output_dir, ignore_errors=True)

        return self

    def predict(self, x_pred: "DashAIDataset") -> List:
        """Translate Spanish source texts to English.

        Parameters
        ----------
        x_pred : DashAIDataset
            Source-language dataset. Only the first column is used.

        Returns
        -------
        list of str
            One translated string per input sample, in the same order as
            ``x_pred``.

        Raises
        ------
        sklearn.exceptions.NotFittedError
            If the model has not been fine-tuned yet (``fitted`` is ``False``).
        """
        if not self.fitted:
            raise NotFittedError(
                f"This {self.__class__.__name__} instance is not fitted yet. Call 'fit'"
                " with appropriate arguments before using this estimator."
            )

        dataset = self.tokenize_data(x_pred)
        dataset.set_format(type="torch", columns=["input_ids", "attention_mask"])

        translations = []

        for example in dataset:
            inputs = {
                k: v.unsqueeze(0).to(self.model.device) for k, v in example.items()
            }
            outputs = self.model.generate(**inputs)
            translated_text = self.tokenizer.decode(
                outputs[0], skip_special_tokens=True
            )
            translations.append(translated_text)

        return translations

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Return the dataset unchanged.

        No pre-processing transformations are required for this model. The
        method exists for compatibility with the DashAI model interface.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be prepared.
        is_fit : bool, optional
            Whether the call is made during fitting. Unused here. Default
            ``False``.

        Returns
        -------
        DashAIDataset
            The original dataset, unmodified.
        """
        return dataset

    def save(self, filename: Union[str, "Path"]) -> None:
        """Store the fine-tuned model and its configuration to disk.

        Saves the model weights via ``save_pretrained`` and embeds the
        hyperparameters (epochs, batch size, learning rate, etc.) into the
        HuggingFace config so they can be restored by :meth:`load`.

        Parameters
        ----------
        filename : str or Path
            Directory path where the model files will be written. If a file
            exists at that path it is removed and replaced by a directory.
        """
        from transformers import AutoConfig

        save_dir = Path(filename)
        if save_dir.exists() and save_dir.is_file():
            save_dir.unlink()
        save_dir.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(save_dir)
        config = AutoConfig.from_pretrained(save_dir)
        config.custom_params = {
            "num_train_epochs": self.training_args.get("num_train_epochs"),
            "batch_size": self.batch_size,
            "learning_rate": self.training_args.get("learning_rate"),
            "device": self.device,
            "weight_decay": self.training_args.get("weight_decay"),
            "fitted": self.fitted,
        }
        config.save_pretrained(save_dir)

    @classmethod
    def load(cls, filename: Union[str, "Path"]):
        """Restore an OpusMtEsENTransformer instance from disk.

        Reads the HuggingFace config to recover the custom hyperparameters
        saved by :meth:`save`, then reconstructs the seq2seq model and wraps
        it in a new :class:`OpusMtEsENTransformer` instance.

        Parameters
        ----------
        filename : str or Path
            Directory path from which the model files will be read.

        Returns
        -------
        OpusMtEsENTransformer
            The restored model instance with ``fitted`` set to the persisted
            value.
        """
        from transformers import AutoConfig, AutoModelForSeq2SeqLM

        model = AutoModelForSeq2SeqLM.from_pretrained(filename)
        config = AutoConfig.from_pretrained(filename)
        custom_params = getattr(config, "custom_params", {})

        loaded_model = cls(
            model=model,
            num_train_epochs=custom_params.get("num_train_epochs"),
            batch_size=custom_params.get("batch_size"),
            learning_rate=custom_params.get("learning_rate"),
            device=custom_params.get("device"),
            weight_decay=custom_params.get("weight_decay"),
            log_train_every_n_epochs=None,
            log_train_every_n_steps=None,
            log_validation_every_n_epochs=None,
            log_validation_every_n_steps=None,
        )
        loaded_model.fitted = custom_params.get("fitted", False)
        return loaded_model

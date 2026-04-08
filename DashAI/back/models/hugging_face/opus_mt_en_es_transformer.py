"""OpusMtEnESTransformer model for english-spanish translation DashAI implementation."""

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from sklearn.exceptions import NotFittedError

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.translation_model import TranslationModel
from DashAI.back.models.utils import GPU_OR_CPU, GPU_OR_CPU_PLACEHOLDER

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class OpusMtEnESTransformerSchema(BaseSchema):
    """opus-mt-en-es is a transformer pre-trained model that allows translation of
    texts from English to Spanish.
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
        placeholder=4,
        description=MultilingualString(
            en="The batch size per GPU/TPU core/CPU for training",
            es="El tamaño de lote por núcleo GPU/TPU/CPU para entrenamiento",
        ),
        alias=MultilingualString(en="Batch size", es="Tamaño de lote"),
    )  # type: ignore
    learning_rate: schema_field(
        float_field(ge=0.0),
        placeholder=2e-5,
        description=MultilingualString(
            en="The initial learning rate for AdamW optimizer",
            es="La tasa de aprendizaje inicial para el optimizador AdamW",
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
    )  # type: ignore
    device: schema_field(
        enum_field(enum=GPU_OR_CPU),
        placeholder=GPU_OR_CPU_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware on which the training is run. If available, GPU is "
                "recommended for efficiency reasons. Otherwise, use CPU. "
                "If GPU is selected then it will use all gpus available. "
            ),
            es=(
                "Hardware en el que se ejecuta el entrenamiento. Si está disponible, "
                "se recomienda GPU por razones de eficiencia. De lo contrario, use "
                "CPU. Si se selecciona GPU, usará todas las GPUs disponibles."
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


class OpusMtEnESTransformer(TranslationModel):
    """Pre-trained transformer for english-spanish translation.

    This model fine-tunes the pre-trained model opus-mt-en-es.
    """

    SCHEMA = OpusMtEnESTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT En-Es Transformer",
        es="Transformer Opus MT En-Es",
    )
    DESCRIPTION: str = MultilingualString(
        en="Pre-trained transformer for English-Spanish translation.",
        es="Transformer pre-entrenado para traducción inglés-español.",
    )
    COLOR: str = "#FFA500"
    ICON: str = "Translate"

    def __init__(self, model=None, **kwargs):
        """Initialize the transformer.

        This process includes the instantiation of the pre-trained model and the
        associated tokenizer. When ``model`` is ``None`` the Helsinki-NLP
        ``opus-mt-en-es`` checkpoint is downloaded from HuggingFace; when a
        model object is supplied the tokenizer is reused without re-downloading.

        Parameters
        ----------
        model : transformers.PreTrainedModel or None, optional
            An already-loaded HuggingFace translation model to reuse. If
            ``None``, the pre-trained ``Helsinki-NLP/opus-mt-en-es`` checkpoint
            is downloaded and initialised. Default ``None``.
        **kwargs : dict
            Additional hyperparameters forwarded to ``validate_and_transform``
            and used to configure training arguments (e.g. ``batch_size``,
            ``epochs``, ``learning_rate``).
        """
        kwargs = self.validate_and_transform(kwargs)
        from transformers import AutoTokenizer

        self.model_name = "Helsinki-NLP/opus-mt-en-es"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if model is None:
            self.training_args = kwargs
            self.batch_size = kwargs.pop("batch_size", 16)
            self.device = kwargs.pop("device")
            self.log_train_every_n_epochs = kwargs.pop("log_train_every_n_epochs", 1)
            self.log_train_every_n_steps = kwargs.pop("log_train_every_n_steps", None)
            self.log_validation_every_n_epochs = kwargs.pop(
                "log_validation_every_n_epochs", 1
            )
            self.log_validation_every_n_steps = kwargs.pop(
                "log_validation_every_n_steps", None
            )
        if model is None:
            from transformers import AutoModelForSeq2SeqLM

            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        else:
            self.model = model
        self.num_train_epochs = kwargs.get("num_train_epochs", 2)
        self.fitted = model is not None

    def tokenize_data(
        self, x: "DashAIDataset", y: Optional["DashAIDataset"] = None
    ) -> "DashAIDataset":
        """Tokenize input and output.

        Parameters
        ----------
        x: DashAIDataset
            Dataset with the input data to preprocess.
        y: Optional DashAIDataset
            Dataset with the output data to preprocess.

        Returns
        -------
        Dataset
            Dataset with the processed data.
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
    ) -> "OpusMtEnESTransformer":
        """Fine-tune the opus-mt-en-es model on English-Spanish translation data.

        Parameters
        ----------
        x_train : DashAIDataset
            Input English text features for training.
        y_train : DashAIDataset
            Target Spanish translation labels for training.
        x_validation : DashAIDataset, optional
            Input English text features for validation. Defaults to None.
        y_validation : DashAIDataset, optional
            Target Spanish translation labels for validation. Defaults to None.

        Returns
        -------
        OpusMtEnESTransformer
            The fine-tuned model instance.
        """
        from DashAI.back.models.hugging_face.metrics_callback import MetricsCallback

        dataset = self.tokenize_data(x_train, y_train)
        dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

        from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

        training_args = Seq2SeqTrainingArguments(
            output_dir="DashAI/back/user_models/temp_checkpoints_opus-mt-en-es",
            save_steps=1,
            save_total_limit=1,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            use_cpu=self.device.lower() != "gpu",
            **self.training_args,
        )

        # Initialize the custom callback with epoch information
        metrics_callback = MetricsCallback(
            model_instance=self,
            x_train=x_train,
            y_train=y_train,
            x_val=x_validation,
            y_val=y_validation,
            total_epochs=self.num_train_epochs,
            log_training_every_n_epochs=self.log_train_every_n_epochs,
            log_training_every_n_steps=self.log_train_every_n_steps,
            log_val_every_n_epochs=self.log_validation_every_n_epochs,
            log_val_every_n_steps=self.log_validation_every_n_steps,
        )

        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            callbacks=[metrics_callback],
        )

        self.fitted = True
        trainer.train()
        shutil.rmtree(
            "DashAI/back/user_models/temp_checkpoints_opus-mt-en-es", ignore_errors=True
        )
        return self

    def predict(self, x_pred: "DashAIDataset") -> List:
        """Predict with the fine-tuned model.

        Parameters
        ----------
        x_pred : Dataset
            Dataset with text data.

        Returns
        -------
        List
            list of translations made by the model.
        """
        if not self.fitted:
            raise NotFittedError(
                f"This {self.__class__.__name__} instance is not fitted yet. Call 'fit'"
                " with appropriate arguments before using this "
                "estimator."
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
        """Apply the model transformations to the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        try:
            # Useless in this case, but we keep it for consistency with other models.
            return dataset
        except Exception as e:
            print(f"Couldn't apply transformations to the dataset for the model: {e}")

    def save(self, filename: Union[str, "Path"]) -> None:
        """Store the fine-tuned model and its configuration to disk.

        Saves the model weights via ``save_pretrained`` and embeds the
        hyperparameters (epochs, batch size, learning rate, etc.) into the
        Hugging Face config so they can be restored by :meth:`load`.

        Parameters
        ----------
        filename : str or Path
            Directory path where the model files will be written.
        """
        save_dir = Path(filename)
        if save_dir.exists() and save_dir.is_file():
            save_dir.unlink()
        save_dir.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(save_dir)
        from transformers import AutoConfig

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
        """Restore an OpusMtEnESTransformer instance from disk.

        Reads the Hugging Face config to recover the custom hyperparameters
        saved by :meth:`save`, then reconstructs the seq2seq model and wraps
        it in a new :class:`OpusMtEnESTransformer` instance.

        Parameters
        ----------
        filename : str or Path
            Directory path from which the model files will be read.

        Returns
        -------
        OpusMtEnESTransformer
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

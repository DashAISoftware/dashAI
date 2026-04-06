"""NLLB transformer model for multilingual translation DashAI implementation."""

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from sklearn.exceptions import NotFittedError

from DashAI.back.core.schema_fields import schema_field, string_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)
from DashAI.back.models.translation_model import TranslationModel
from DashAI.back.models.utils import GPU_OR_CPU_PLACEHOLDER

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class NllbTransformerSchema(OpusMtEnESTransformerSchema):
    """Schema for NLLB multilingual translation model."""

    source_language: schema_field(
        string_field(),
        placeholder="spa_Latn",
        description=MultilingualString(
            en=(
                "Source language code for NLLB tokenizer. "
                "Example: spa_Latn for Spanish."
            ),
            es=(
                "Codigo de idioma de origen para el tokenizer NLLB. "
                "Ejemplo: spa_Latn para espanol."
            ),
        ),
        alias=MultilingualString(en="Source language", es="Idioma de origen"),
    )  # type: ignore
    target_language: schema_field(
        string_field(),
        placeholder="eng_Latn",
        description=MultilingualString(
            en=(
                "Target language code for NLLB generation. "
                "Example: eng_Latn for English."
            ),
            es=(
                "Codigo de idioma destino para la generacion NLLB. "
                "Ejemplo: eng_Latn para ingles."
            ),
        ),
        alias=MultilingualString(en="Target language", es="Idioma destino"),
    )  # type: ignore


class NllbTransformer(TranslationModel):
    """NLLB model for configurable multilingual translation."""

    SCHEMA = NllbTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="NLLB Transformer",
        es="Transformer NLLB",
    )
    DESCRIPTION: str = MultilingualString(
        en=("NLLB multilingual model for configurable source-target translation."),
        es=("Modelo multilenguaje NLLB para traduccion configurable origen-destino."),
    )
    COLOR: str = "#5E35B1"
    ICON: str = "Translate"

    def __init__(self, model=None, **kwargs):
        """Initialize the NLLB tokenizer and model."""
        kwargs = self.validate_and_transform(kwargs)

        from transformers import AutoTokenizer

        self.model_name = "facebook/nllb-200-distilled-600M"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        self.source_language = kwargs.get("source_language", "spa_Latn")
        self.target_language = kwargs.get("target_language", "eng_Latn")

        lang_code_to_id = getattr(self.tokenizer, "lang_code_to_id", None)
        if not isinstance(lang_code_to_id, dict) or not lang_code_to_id:
            raise ValueError("NLLB tokenizer does not expose supported language codes.")
        if self.source_language not in lang_code_to_id:
            raise ValueError(f"Unsupported source_language '{self.source_language}'.")
        if self.target_language not in lang_code_to_id:
            raise ValueError(f"Unsupported target_language '{self.target_language}'.")

        self.tokenizer.src_lang = self.source_language

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
        """Tokenize input and optional output datasets for NLLB."""
        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        self.tokenizer.src_lang = self.source_language

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
    ) -> "NllbTransformer":
        """Train NLLB for the configured language pair."""
        from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

        from DashAI.back.models.hugging_face.metrics_callback import MetricsCallback

        dataset = self.tokenize_data(x_train, y_train)
        dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

        has_validation_data = x_validation is not None and y_validation is not None

        output_root = Path("DashAI/back/user_models/temp_checkpoints_nllb")
        output_root.mkdir(parents=True, exist_ok=True)
        run_output_dir = tempfile.mkdtemp(prefix="nllb_", dir=str(output_root))

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
        """Generate translations using NLLB target language forcing."""
        if not self.fitted:
            raise NotFittedError(
                f"This {self.__class__.__name__} instance is not fitted yet. Call 'fit'"
                " with appropriate arguments before using this estimator."
            )

        dataset = self.tokenize_data(x_pred)
        dataset.set_format(type="torch", columns=["input_ids", "attention_mask"])

        translations = []
        target_bos = self.tokenizer.lang_code_to_id[self.target_language]

        for example in dataset:
            inputs = {
                k: v.unsqueeze(0).to(self.model.device) for k, v in example.items()
            }
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=target_bos,
            )
            translated_text = self.tokenizer.decode(
                outputs[0], skip_special_tokens=True
            )
            translations.append(translated_text)

        return translations

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Keep compatibility with model preprocessing hook."""
        return dataset

    def save(self, filename: Union[str, "Path"]) -> None:
        """Save model and custom configuration."""
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
            "source_language": self.source_language,
            "target_language": self.target_language,
            "fitted": self.fitted,
        }
        config.save_pretrained(save_dir)

    @classmethod
    def load(cls, filename: Union[str, "Path"]):
        """Load model from disk."""
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
            source_language=custom_params.get("source_language", "spa_Latn"),
            target_language=custom_params.get("target_language", "eng_Latn"),
            log_train_every_n_epochs=None,
            log_train_every_n_steps=None,
            log_validation_every_n_epochs=None,
            log_validation_every_n_steps=None,
        )
        loaded_model.fitted = custom_params.get("fitted", False)
        return loaded_model
